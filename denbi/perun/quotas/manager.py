from novaclient import client as novaClient
from cinderclient.v3 import client as cinderClient
from neutronclient.v2_0 import client as neutronClient
from denbi.perun.quotas import component as component


class QuotaFactory:
    """
    Factory for OpenStack quotas.

    This factory allows you to create quota managers for a given project.
    It hides the internal management of authentication sessions and reduces
    the amount of objects to be passed around in higher level codeself.
    """

    def __init__(self, session):
        """
        Initializes the factory

        :param session: an initialized OpenStack session to use for the
                        various component clients
        """

        self._nova = novaClient.Client(2, session=session, endpoint_type="public")
        self._cinder = cinderClient.Client(2, session=session, endpoint_type="public")
        self._neutron = neutronClient.Client(session=session, endpoint_type="public")

    def get_manager(self, project_id):
        """
        Constructs a quota manager for the given projectself.

        :param project_id: manager is built for the given project and its quotas

        """

        return QuotaManager(project_id, self._nova, self._cinder, self._neutron)


class QuotaManager:
    """
    High-level class for managing OpenStack quotasself.

    This class manages the various openstack component clients and passed
    requests to get, check and update quotas to the corresponding
    implementation.

    """

    # Mapping of quota names to their components.
    # The values are taken from the example REST responses in the component's\
    # official API docs.
    # Some quotas are defined in multiple places (e.g. nova vs. neutron),
    # but the quotas have different names. Do not use the deprecated ones
    # e.g. the nova networking quotas.
    #
    # de.NBI also defines some quotas of their own; currently there's no
    # support for these quotas. Their name is mapped to the None value,
    # which is recognized as a defined, but not implemented quota in
    # the class.
    #
    # TODO: can we build the mapping dynamically, e.g. by getting
    #       the default value for each component?
    NOVA = 'nova'
    CINDER = 'cinder'
    NEUTRON = 'neutron'
    QUOTA_MAPPING = {'cores': NOVA,
                     'fixed_ips': NOVA,
                     'floating_ips': NOVA,
                     'injected_file_content_bytes': NOVA,
                     'injected_files': NOVA,
                     'injected_file_path_bytes': NOVA,
                     'instances': NOVA,
                     'key-pairs': NOVA,
                     'metadata_items': NOVA,
                     'ram': NOVA,
                     'security_group_rules': NOVA,
                     'security_groups': NOVA,
                     'server_group_members': NOVA,
                     'server_groups': NOVA,

                     'volumes': CINDER,
                     'snapshots': CINDER,
                     'backups': CINDER,
                     'groups': CINDER,
                     'per_volume_gigabytes': CINDER,
                     'gigabytes': CINDER,
                     'backup_gigabytes': CINDER,

                     'floatingip': NEUTRON,
                     'rbac_policy': NEUTRON,
                     'subnet': NEUTRON,
                     'subnetpool': NEUTRON,
                     'security_group_rule': NEUTRON,
                     'security_group': NEUTRON,
                     'port': NEUTRON,
                     'router': NEUTRON,
                     'network': NEUTRON,

                     'strange_denbi_quota': None}

    def __init__(self, project_id, nova, cinder, neutron):
        """
        Initializes a quota manager for the given project

        :param project_id: the project to manage
        :param nova: nova client instance
        :param cinder: cinder client instance
        :param neutron: neutron client instance

        """
        self._components = {self.NOVA: component.QuotaComponentFactory.get_component(nova, project_id),
                            self.CINDER: component.QuotaComponentFactory.get_component(cinder, project_id),
                            self.NEUTRON: component.QuotaComponentFactory.get_component(neutron, project_id)}

    def _map_to_component(self, name):
        if name in self.QUOTA_MAPPING:
            if self.QUOTA_MAPPING[name] is None:
                return None
            return self._components[self.QUOTA_MAPPING[name]]
        else:
            raise ValueError("Quota name %s is invalid" % name)

    def get_current_quota(self, name):
        """
        Return the current quota value with the given name.

        If the name is invalid, a ValueError exception is
        thrown. If the name refers to an unimplemented quota
        like special de.NBI quotas, None is returned.
        """
        component = self._map_to_component(name)
        if component is not None:
            return component.get_value(name)
        return None

    def get_current_in_use(self, name):
        """
        Returns the current amount of resource in use for the given quota.

        :param name: name of the quota to check
        """
        component = self._map_to_component(name)
        if component is not None:
            return component.get_in_use(name)
        return None

    def check_value(self, name, value):
        """
        Checks whether the given value is suitable a new quota value.

        Returns true if the value is OK, false otherwise (e.g. conflict
        with currently used resources).

        If the name refers to an invalid value, a ValueError exception is
        thrown. In case of am unimplemented quota the method always
        returns true.

        :param name: quota to check
        :param value: new value for quota

        :returns: boolean to indicate whether value is suitable
        """
        component = self._map_to_component(name)
        if component is None:
            return True
        else:
            return component.check_value(name, value)

    def set_value(self, name, value):
        """
        Sets the given quota to the given value.

        The implementation checks whether the given value is valid and
        updates the quota. If the value is invalid or the name is invalid,
        the method throws a ValueError exception. If the value is None
        the named quota left unchanged

        :param name: name of the quota to set
        :param quota: new value of the quota
        """
        component = self._map_to_component(name)
        if component is not None and value is not None:
            component.set_quota(name, value)
