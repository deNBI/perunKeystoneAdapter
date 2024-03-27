def test_user(test, denbiuser, perun_id=None, elixir_id=None, elixir_name=None, email=None, enabled=True, ssh_key=None, deleted=False):
    """ Test if an given denbi user object conforms with the given values."""
    test.assertEqual(denbiuser['perun_id'], perun_id)
    # if user is deleted we do not have to check anything else:
    if deleted:
        test.assertEqual(denbiuser['enabled'], False)
        test.assertEqual(denbiuser['deleted'], True)
    else:
        test.assertEqual(denbiuser['elixir_id'], str(elixir_id))
        test.assertEqual(denbiuser['elixir_name'], str(elixir_name))
        test.assertEqual(denbiuser['email'], str(email))
        test.assertEqual(denbiuser['ssh_key'], str(ssh_key))
        test.assertEqual(denbiuser['enabled'], enabled)


def test_project(test, denbiproject, perun_id=None, members=[], enabled=True, deleted=False):
    """ Test if denbi project object conforms with the given values."""
    test.assertEqual(denbiproject['perun_id'], perun_id)
    # if project is deleted we do not have to check anything else
    if deleted:
        test.assertEqual(denbiproject['enabled'], False)
        test.assertEqual(denbiproject['scratched'], True)
    else:
        test.assertSetEqual(set(denbiproject['members']), set(members))
        test.assertEqual(denbiproject['enabled'], enabled)
