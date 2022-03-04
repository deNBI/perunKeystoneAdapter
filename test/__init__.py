def test_user(test, denbiuser, perun_id=None, elixir_id=None, elixir_name=None, email=None, enabled=True, ssh_key=None, deleted=False):
    test.assertEqual(denbiuser['perun_id'], perun_id)
    test.assertEqual(denbiuser['elixir_id'], elixir_id)
    test.assertEqual(denbiuser['elixir_name'], elixir_name)
    if email is not None:
        test.assertEqual(denbiuser['email'], email)
    if ssh_key is not None:
        test.assertEqual(denbiuser['ssh_key'], ssh_key)
    if deleted:
        test.assertEqual(denbiuser['enabled'], False)
        test.assertEqual(denbiuser['deleted'], True)
    else:
        test.assertEqual(denbiuser['enabled'], enabled)

def test_project(test, denbiproject, perun_id=None, members=[], enabled=True, deleted=False):
    test.assertEqual(denbiproject['perun_id'], perun_id)
    test.assertSetEqual(set(denbiproject['members']), set(members))
    if deleted:
        test.assertEqual(denbiproject['enabled'], False)
        test.assertEqual(denbiproject['scratched'], True)
    else:
        test.assertEqual(denbiproject['enabled'], enabled)