from neutronclient.v2_0 import client as neutronClient
from cinderclient.v3 import client as cinderClient
from novaclient.v2 import client as novaClient
import threading
import logging
import abc


class QuotaComponentFactory:
    """
    Simple factory class to create the right kind of component implementation
    for a given openstack clientself.
    """

    @staticmethod
    def get_component(client, project_id):
        """
        Return a quota management component for the given client to be
        used with the given project.
        """
        if isinstance(client, neutronClient.Client):
            return NeutronQuotaComponent(client, project_id)
        elif isinstance(client, cinderClient.Client):
            return CinderQuotaComponent(client, project_id)
        elif isinstance(client, novaClient.Client):
            return NovaQuotaComponent(client, project_id)
        else:
            raise ValueError("Unsupport client " + str(client))


class QuotaComponent:
    """
    Base class for quotas defined in an OpenStack component.

    This class defines the necessary method to retrieve the current values
    (if any), checks a new values and finally updates the quotas in the
    component.

    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, client, project_id):
        """
        Initializes the quota component instance

        :param client: the openstack client to use, e.g. an instance of novaclient
        :param name: name of the quota to manage
        :param project_id: project to query quotas for
        """

        self.logger = logging.getLogger('denbi')
        self._client = client
        self._project_id = project_id
        self._quota_cache = None
        self._lock = threading.Lock()

    def get_value(self, name):
        """
        Get the current value for the quota given by its name.

        :param name: name of the quota to retrieve

        Retrieves the (maybe cached) value of the given quota.
        If the name is invalid, this method throws a ValueError
        exception.
        """

        if self._quota_cache is None:
            # quota is not initialized yet, so get the lock and
            # query all quotas
            with self._lock:
                if self._quota_cache is None:
                    self._quota_cache = self._get_cache()

        if name in self._quota_cache:
            return self._quota_cache[name]['limit']
        raise ValueError("Unknown quota " + name + " in component " + str(self._client))

    @abc.abstractmethod
    def _get_cache(self):
        """
        Method to return the quota cache with the quota values and the
        amount of currently used resources
        """
        return

    def get_in_use(self, name, consider_reserved=True):
        """
        Returns the amounf ot resource controlled by the given qouta
        that are currently in use

        :param name: name of the quota to check resource usage for
        :param consider_reserved: also include the reserved resources
        """
        # retrieve quota value to get the in use values
        self.get_value(name)
        if consider_reserved:
            return self._quota_cache[name]['in_use'] + self._quota_cache[name]['reserved']
        else:
            return self._quota_cache[name]['in_use']

    def check_value(self, name, value):
        """
        Compares the given value with the current value and returns
        true if the current value is acceptable as new quota value.

        This method also tries to check the real amount of resources
        currently in use if the corresponding value is available.

        :param name: name of the quota to check
        :param value: new value for the quota

        :returns: boolean indicating whether the given value is
                  acceptable a new quota value

        If name is an invalid quota name, this method throws a
        ValueError exception.
        """

        current_quota = self.get_value(name)
        if value is None:
            # skip further checks if no quota should be set
            return True

        if value == -1:
            # -1 is unrestricted quota.
            # TODO: do we want to support setting this?
            return True

        if value > current_quota:
            # we can always extend the quota
            # if setting the new quota fails, e.g. due to quotas
            # on a parent project in a nested project setup,
            # setting the quota will fail.
            # TODO: do we have a way to check this?
            return True

        # we need to check whether the currently used resources
        # exceed the new value
        self.logger.debug("Currently in use for quota %s: %d", name, self.get_in_use(name))
        return self.get_in_use(name) <= value

    def set_quota(self, name, value):
        """
        Sets the given quota to the given value.

        This method performs a check with check_value, and sets the given
        quota if necessary. If the check fails, this method throws a ValueError
        exception.

        :param name: name of the quota to set
        :param value: new value for the quota

        """
        if value is None:
            return
        self.logger.debug("Attempt to set quota value %s for quota %s in component %s",
                          value, name, self._client)
        if self.check_value(name, value):
            if self.get_value(name) != value:
                self._set_new_quota(name, value)
                self.logger.info("Set quota value %s for quota %s in component %s",
                                 value, name, self._client)
                self._quota_cache[name]['limit'] = value
        else:
            raise ValueError("New quota of %s for %s exceed currently used resource amount".format(value, name))

    @abc.abstractmethod
    def _set_new_quota(self, name, value):
        """
        Abstract method to set a new quota value
        """
        return

    def _set_neutron_quota(self, name, value):
        raise Exception("Not implemented yet")

    def flush(self):
        """
        Flushes the internal quota cache and enforces a reload on next request.
        """
        with self._lock:
            self._quota_cache = None


class SimpleQuotaComponent(QuotaComponent):
    """
    Class used for clients with a 'QuotaSet' fields supporting
    getting and setting quotas
    """

    def _set_new_quota(self, name, value):
        # TODO: the APIs are migrating to a stricter form of
        #       parameter passing (named parameters instead of dict)
        #       how do we do this correctly with the new calls?
        self._client.quotas.update(self._project_id, **{name: value})


class NovaQuotaComponent(SimpleQuotaComponent):
    def _get_cache(self):
        return self._client.quotas.get(self._project_id, detail=True).to_dict()


class CinderQuotaComponent(SimpleQuotaComponent):
    def _get_cache(self):
        return self._client.quotas.get(self._project_id, usage=True).to_dict()


class NeutronQuotaComponent(QuotaComponent):
    """
    Neutron client has a different APIs, and thus requires a more complex
    quota implementation.
    """

    def _get_cache(self):
        # neutronclient does not provide a simple method to retrieve the
        # quotas and used resource, but we can query the API manually...
        quotas = self._client.get((self._client.quota_path + "/details.json")
                                  % self._project_id)['quota']
        # neutron uses different field names, so change the names...
        for key in quotas.keys():
            quotas[key]['in_use'] = quotas[key].pop('used', None)
        return quotas

    def _set_new_quota(self, name, value):
        self._client.update_quota(self._project_id,
                                  body={'quota': {name: value}})
