'''
Created on Jan 28, 2011

@author: camerondawson
'''
from features.models import TestcaseModel, UserModel, TestrunModel, \
    EnvironmentModel, ProductModel, TestcycleModel, TestsuiteModel
from features.tcm_data_helper import get_stored_or_store_name, eq_, ns, jstr, \
    json_to_obj, verify_single_item_in_list, get_testcase_status_id
from features.tcm_request_helper import get_form_headers, do_delete, do_post, \
    do_put, get_resource_identity
from lettuce import step, world



'''
######################################################################

                     TEST CASE STEPS

######################################################################
'''

@step(u'create a new testcase with (that name|name "(.*)")')
def create_testcase_with_name_foo(step, stored, name):
    name = get_stored_or_store_name("testcase", stored, name)

    post_payload = {"productId": ProductModel().get_seed_resid()[0],
                    "maxAttachmentSizeInMbytes":"10",
                    "maxNumberOfAttachments":"5",
                    "name": name,
                    "description": "Lettuce tc"
                   }
    do_post(world.path_testcases,
            post_payload)


@step(u'user with (that name|name "(.*)") creates a new testcase with (that name|name "(.*)")')
def user_creates_testcase_with_name(step, stored_user, user_name, stored_testcase, testcase_name):
    userModel = UserModel()
    user_name = userModel.get_stored_or_store_name(stored_user, user_name)
    testcaseModel = TestcaseModel()
    testcase_name = testcaseModel.get_stored_or_store_name(stored_testcase, testcase_name)

    post_payload = {"productId": ProductModel().get_seed_resid()[0],
                    "maxAttachmentSizeInMbytes":"10",
                    "maxNumberOfAttachments":"5",
                    "name": testcase_name,
                    "description": "Lettuce tc"
                    }
    headers = get_form_headers(userModel.get_auth_header(user_name))
    do_post(testcaseModel.root_path,
            post_payload,
            headers = headers)

@step(u'testcase with (that name|name "(.*)") (exists|does not exist)')
def check_testcase_foo_existence(step, stored, name, existence):
    name = get_stored_or_store_name("testcase", stored, name)
    TestcaseModel().verify_existence_on_root (name,
                                              existence = existence)


@step(u'delete the testcase with (that name|name "(.*)")')
def delete_testcase_with_name_foo(step, stored, name):
    name = get_stored_or_store_name("testcase", stored, name)

    testcase_id, version = TestcaseModel().get_resid(name)
    do_delete(world.path_testcases + str(testcase_id),
              {"originalVersionId": version})


@step(u'add these steps to the testcase with (that name|name "(.*)")')
def add_steps_to_testcase_name(step, stored, name):
    name = get_stored_or_store_name("testcase", stored, name)
    tcModel = TestcaseModel()
    # first we need the testcase id so we can get the latest version to add steps to
    testcase_id = tcModel.get_resid(name)[0]

    testcaseversion_id = tcModel.get_latestversion_resid(testcase_id)[0]

    uri = world.path_testcases + "versions/" + str(testcaseversion_id) + "/steps/"
    for case_step in step.hashes:
        do_post(uri, case_step)

@step(u'the testcase with (that name|name "(.*)") has these steps')
def verify_testcase_steps(step, stored, name):
    tcModel = TestcaseModel()
    name = tcModel.get_stored_or_store_name(stored, name)

    testcasestep_list = tcModel.get_latest_steps_list(name)

    # compare the returned values with those passed in to verify match
    step_num = 0
    try:
        for exp_step in step.hashes:
            act_step = testcasestep_list[step_num]
            eq_(act_step[ns("name")], exp_step["name"], "name match")
            step_num += 1
    except KeyError:
        assert False, "Object field mismatch.\nExpected:\n" + jstr(step.hashes) + "\n\nActual:\n" + jstr(testcasestep_list)


@step(u'user with (that name|name "(.*)") approves the testcase with (that name|name "(.*)")')
def user_approves_testcase(step, stored_user, user_name, stored_testcase, testcase_name):
    testcase_name = get_stored_or_store_name("testcase", stored_testcase, testcase_name)
    user_name = get_stored_or_store_name("user", stored_user, user_name)

    tcModel = TestcaseModel()
    # first we need the testcase id so we can get the latest version to approve
    testcase_id, version = tcModel.get_resid(testcase_name)
    testcaseversion_id = tcModel.get_latestversion_resid(testcase_id)[0]


    # do the approval of the testcase
    uri = world.path_testcases + "versions/%s/approve/" % (testcaseversion_id)
    headers = get_form_headers(UserModel().get_auth_header(user_name))

    do_put(uri,
           {"originalVersionId": version},
            headers = headers)

@step(u'user with (that name|name "(.*)") approves the following testcases')
def user_approves_testcases(step, stored_user, user_name):
    user_name = get_stored_or_store_name("user", stored_user, user_name)

    tcModel = TestcaseModel()

    for tc in step.hashes:

        # first we need the testcase id so we can get the latest version to approve
        testcase_id, version = tcModel.get_resid(tc["name"])
        testcaseversion_id = tcModel.get_latestversion_resid(testcase_id)[0]


        # do the approval of the testcase
        uri = world.path_testcases + "versions/%s/approve/" % (testcaseversion_id)
        headers = get_form_headers(UserModel().get_auth_header(user_name))

        do_put(uri,
               {"originalVersionId": version},
                headers = headers)

@step(u'assign the following testcases to the user with (that name|name "(.*)") for the testrun with (that name|name "(.*)")')
def assign_testcases_to_user_for_testrun(step, stored_user, user_name, stored_testrun, testrun_name):
    '''
        Expect hashes to contain:
        | testcase name |
    '''
    user_name = get_stored_or_store_name("user", stored_user, user_name)
    user_id = UserModel().get_resid(user_name)[0]
    testrun_name = get_stored_or_store_name("testrun", stored_testrun, testrun_name)
    trModel = TestrunModel()
    testrun_id, testrun_version = trModel.get_resid(testrun_name)

    # get the list of testcases for this testrun
    includedtestcase_list = trModel.get_included_testcases(testrun_id)

    for tc in step.hashes:
        testcase_id = TestcaseModel().get_resid(tc["name"])[0]
        # find that in the list of testcases
        includedtestcase = verify_single_item_in_list(includedtestcase_list, "testCaseId", testcase_id)

        includedtestcase_id = get_resource_identity(includedtestcase)[0]

        post_uri = world.path_testruns + "includedtestcases/%s/assignments/" % includedtestcase_id
        body = {"testerId": user_id, "originalVersionId": testrun_version}

        do_post(post_uri, body)



@step(u'activate the testcase with (that name|name "(.*)")')
def activate_testcase_with_name(step, stored, name):
    name = get_stored_or_store_name("testcase", stored, name)

    tcModel = TestcaseModel()

    testcase_id = tcModel.get_resid(name)[0]
    testcaseversion_id, version = tcModel.get_latestversion_resid(testcase_id)

    do_put(world.path_testcases + "versions/%s/activate" % testcaseversion_id,
              {"originalVersionId": version})



@step(u'activate the following testcases')
def activate_testcases(step):

    tcModel = TestcaseModel()

    for tc in step.hashes:

        # first we need the testcase id so we can get the latest version to approve
        testcase_id = tcModel.get_resid(tc["name"])[0]
        testcaseversion_id, version = tcModel.get_latestversion_resid(testcase_id)

        do_put(world.path_testcases + "versions/%s/activate" % testcaseversion_id,
                  {"originalVersionId": version})


#@todo: This has a hardcoded value for approvalStatusId, fix that
@step(u'the testcase with (that name|name "(.*)") has approval status of Active')
def testcase_has_status_of_approved(step, stored, testcase_name):
    testcase_name = get_stored_or_store_name("testcase", stored, testcase_name)

    tcModel = TestcaseModel()
    # fetch the steps for this testcase from the latestversion
    testcase_id = tcModel.get_resid(testcase_name)[0]
    testcaseversion = tcModel.get_latestversion(testcase_id)
    # should be just one
    try:
        eq_(testcaseversion[ns("approvalStatusId")], 2, "Testcase is approved: " + str(testcaseversion))
    except KeyError:
        assert False, "Object field mismatch.\nExpected:\n" + ns("approved") + "\n\nActual:\n" + jstr(testcaseversion)

@step(u'the following testcases have the following approval statuses')
def testcases_have_approval_statuses(step):
    for tc in step.hashes:
        pass
    assert False, "need to implement"

@step(u'user with (that name|name "(.*)") marks the following testcase result statuses for the testrun with (that name|name "(.*)")')
def user_marks_testcase_status(step, stored_user, user_name, stored_testrun, testrun_name):
    testrun_name = get_stored_or_store_name("testrun", stored_testrun, testrun_name)
    user_name = get_stored_or_store_name("user", stored_user, user_name)
    status_map = {"Passed": "finishsucceed",
                  "Failed": "finishfail",
                  "Invalidated": "finishinvalidate"}
    # first we need the testrun id so we can get the latest version to approve
#    user_id = UserModel().get_resid(user_name)[0]
    trModel = TestrunModel()
    testrun_id = trModel.get_resid(testrun_name)[0]

    # get the list of testcases for this testrun
    includedtestcase_list = trModel.get_included_testcases(testrun_id)

    for tc in step.hashes:
        testcase_id = TestcaseModel().get_resid(tc["name"])[0]

        result = trModel.get_result(testcase_id, includedtestcase_list)

        result_id, result_version = get_resource_identity(result)

        # start the test
        headers = get_form_headers(UserModel().get_auth_header(user_name))
        testresult = do_put(world.path_testruns + "results/%s/start" % (result_id),
                            {"originalVersionId": result_version}, headers)
        started_result = json_to_obj(testresult)[ns("testresult")][0]

        started_result_version = get_resource_identity(started_result)[1]
        # now finally mark it with the specified status

        do_put(world.path_testruns + "results/%s/%s" % (result_id, status_map[tc["status"]]),
               {"originalVersionId": started_result_version}, headers)


@step(u'the following testcases have the following result statuses for (that testrun|the testrun with name "(.*)")')
def testcases_have_result_statuses(step, stored_testrun, testrun_name):
    trModel = TestrunModel()
    testrun = trModel.get_stored_or_store_obj(stored_testrun, testrun_name)

    testrun_id = get_resource_identity(testrun)[0]

    # get the list of testcases for this testrun
    includedtestcase_list = trModel.get_included_testcases(testrun_id)

    for tc in step.hashes:
        testcase_id = TestcaseModel().get_resid(tc["name"])[0]

        result = trModel.get_result(testcase_id, includedtestcase_list)

        # ok, we have the tc result in question, now check that its status matches expectations
        eq_(result[ns("testRunResultStatusId")],
            get_testcase_status_id(tc["status"]),
            "testRunResultStatusId check")


@step(u'(that testrun|the testrun with name "(.*)") has the following result status summary counts')
def testrun_has_summary_counts(step, stored_testrun, testrun_name):
    trModel = TestrunModel()

    testrun = trModel.get_stored_or_store_obj(stored_testrun, testrun_name)

    testrun_id = get_resource_identity(testrun)[0]

    # get the list of testcases for this testrun
    summary_list = trModel.get_summary_list(testrun_id)

    # walk through and verify that each testcase has the expected status
    for category in step.hashes:
        # find that in the list of testcases
        status_id = get_testcase_status_id(category["name"])
        categoryInfo = verify_single_item_in_list(summary_list, "categoryName",
                                                  status_id)
        assert str(categoryInfo[ns("categoryValue")]) == category["count"], \
            "%s count was wrong.  Expected categoryName: %s , categoryValue: %s:\n%s" % \
            (category["name"], status_id, category["count"], jstr(categoryInfo))



@step(u'add environment "(.*)" to test case "(.*)"')
def add_environment_foo_to_test_case_bar(step, environment, test_case):
    # this takes 2 requests.
    #    1: get the id of this test case
    #    2: add the environment to the test case

    # fetch the test case's resource identity
    test_case_id, version = TestcaseModel().get_resid(test_case)

    post_payload = {"name": "test environment"}
    do_post(world.path_testcases + "%s/environments" % (test_case_id),
            post_payload,
            params = {"originalVersionId": version})

@step(u'remove environment "(.*)" from test case "(.*)"')
def remove_environment_from_test_case(step, environment, test_case):
    # fetch the test case's resource identity
    test_case_id, version = TestcaseModel().get_resid(test_case)
    environment_id = EnvironmentModel().get_resid(environment)

    do_delete(world.path_testcases + "%s/environments/%s" % (test_case_id, environment_id),
              {"originalVersionId": version})

@step(u'testcase "(.*)" (has|does not have) environment "(.*)"')
def test_case_foo_has_environment_bar(step, test_case, haveness, environment):
    # fetch the test case's resource identity
    testcaseModel = TestcaseModel()
    testcase_id = testcaseModel.get_resid(test_case)[0]


    environment_list = testcaseModel.get_environment_list(testcase_id)

    #@todo: this should be abstracted into a helper method or in the model
    found_item = [x for x in environment_list if x[ns("name")] == environment]
    if (haveness == "has"):
        assert len(found_item) == 1, "Expected to find %s in:\n%s" % (environment,
                                                                 jstr(environment_list))
    else:
        assert len(found_item) == 0, "Expected to NOT find %s in:\n%s" % (environment,
                                                                 jstr(environment_list))


@step(u'testcase with name "(.*)" (has|does not have) attachment with filename "(.*)"')
def test_case_foo_has_attachment_bar(step, test_case, haveness, attachment):
    # fetch the test case's resource identity
    testcaseModel = TestcaseModel()
    testcase_id = testcaseModel.get_resid(test_case)[0]

    result_list = testcaseModel.get_attachment_list(testcase_id)

    #@todo: this should be abstracted into a helper method or in the model
    found_item = [x for x in result_list if x[ns("name")] == attachment]
    if (haveness == "has"):
        assert len(found_item) == 1, "Expected to find %s in:\n%s" % (attachment,
                                                                 jstr(result_list))
    else:
        assert len(found_item) == 0, "Expected to NOT find %s in:\n%s" % (attachment,
                                                                 jstr(result_list))



'''
######################################################################

                     TESTCYCLE STEPS

######################################################################
'''
@step(u'create a new testcycle with (that name|name "(.*)")')
def create_testcycle_with_name(step, stored, name):
    name = get_stored_or_store_name("testcycle", stored, name)

    post_payload = {"name": name,
                    "description": "Ahh, the cycle of life...",
                    "productId": ProductModel().get_seed_resid()[0],
                    "startDate": "2011/02/02",
                    "communityAuthoringAllowed": "true",
                    "communityAccessAllowed": "true",
                    "endDate": "2014/02/02"
                   }

    do_post(world.path_testcycles,
            post_payload)

@step(u'create the following new testcycles:')
def create_testcycles(step):

    for item in step.hashes:
        # must do this or it will freak out the lettuce reporting, because
        # we delete items from this before submitting.
        testcycle = item.copy()
        # persist the last one we make.  Sometimes we will only make one.
        world.names["testcycle"] = testcycle["name"]

        # get the product id from the passed product name
        product_id = ProductModel().get_resid(testcycle["product name"])[0]

        testcycle["productId"] = product_id

        if testcycle.has_key('product name'):
            del testcycle['product name']

        do_post(world.path_testcycles,
                testcycle)


@step(u'testcycle with (that name|name "(.*)") (exists|does not exist)')
def check_testcycle_foo_existence(step, stored, name, existence):
    name = get_stored_or_store_name("testcycle", stored, name)
    TestcycleModel().verify_existence_on_root(name,
                                              existence = existence)


@step(u'delete the testcycle with (that name|name "(.*)")')
def delete_testcycle_with_name_foo(step, stored, name):
    name = get_stored_or_store_name("testcycle", stored, name)

    testcycle_id, version = TestcycleModel().get_resid(name)

    do_delete(world.path_testcycles + str(testcycle_id),
                                  {"originalVersionId": version})

@step(u'activate the testcycle with (that name|name "(.*)")')
def activate_testrun_with_name(step, stored, name):
    name = get_stored_or_store_name("testcycle", stored, name)

    testcycle_id, version = TestcycleModel().get_resid(name)

    do_put(world.path_testcycles + "%s/activate" % testcycle_id,
              {"originalVersionId": version})



'''
######################################################################

                     TESTSUITE STEPS

######################################################################
'''

@step(u'create a new testsuite with (that name|name "(.*)")')
def create_testsuite_with_name(step, stored, name):
    name = get_stored_or_store_name("testsuite", stored, name)

    post_payload = {"productId": ProductModel().get_seed_resid()[0],
                    "name": name,
                    "description": "Sweet Relief",
                    "useLatestVersions": "true"
                   }

    do_post(world.path_testsuites,
            post_payload)

@step(u'create the following new testsuites:')
def create_testsuites(step):

    for item in step.hashes:
        # must do this or it will freak out the lettuce reporting, because
        # we delete items from this before submitting.
        testsuite = item.copy()
        # persist the last one we make.  Sometimes we will only make one.
        world.names["testcycle"] = testsuite["name"]

        # get the product id from the passed product name
        product_id = ProductModel().get_resid(testsuite["product name"])[0]

        testsuite["productId"] = product_id

        if testsuite.has_key('product name'):
            del testsuite['product name']

        do_post(world.path_testsuites,
                testsuite)

@step(u'activate the testsuite with (that name|name "(.*)")')
def activate_testsuite_with_name(step, stored, name):
    name = get_stored_or_store_name("testsuite", stored, name)

    testsuite_id, version = TestsuiteModel().get_resid(name)

    do_put(world.path_testsuites + "%s/activate" % testsuite_id,
              {"originalVersionId": version})


@step(u'testsuite with (that name|name "(.*)") (exists|does not exist)')
def check_testsuite_foo_existence(step, stored, name, existence):
    name = get_stored_or_store_name("testsuite", stored, name)
    TestsuiteModel().verify_existence_on_root(name,
                                              existence = existence)


@step(u'delete the testsuite with (that name|name "(.*)")')
def delete_testsuite_with_name_foo(step, stored, name):
    name = get_stored_or_store_name("testsuite", stored, name)

    testsuite_id, version = TestsuiteModel().get_resid(name)

    do_delete(world.path_testsuites + str(testsuite_id),
              {"originalVersionId": version})

@step(u'add the following testcases to the testsuite with (that name|name "(.*)")')
def add_testcases_to_testsuite(step, stored, name):
    name = get_stored_or_store_name("testsuite", stored, name)
    testsuite_id, version = TestsuiteModel().get_resid(name)
    tcModel = TestcaseModel()

    for tc in step.hashes:
        tc_id = tcModel.get_resid(tc["name"])[0]
        tc_ver_id = tcModel.get_latestversion_resid(tc_id)[0]

        uri = world.path_testsuites + "%s/includedtestcases" % (testsuite_id)
        do_post(uri,
                {"testCaseVersionId": tc_ver_id,
                 "priorityId": 1,
                 "runOrder": 1,
                 "blocking": "false",
                 "originalVersionId": version})

@step(u'add the following testsuites to the testrun with (that name|name "(.*)")')
def add_testsuites_to_testrun(step, stored, name):
    name = get_stored_or_store_name("testrun", stored, name)
    testrun_id, version = TestrunModel().get_resid(name)

    for testsuite in step.hashes:
        testsuite_id = TestsuiteModel().get_resid(testsuite["name"])[0]

        uri = world.path_testruns + "%s/includedtestcases/testsuite/%s" % (testrun_id, testsuite_id)
        do_post(uri,
                {"originalVersionId": version})

@step('create the seed testcycle, testrun and testcases')
def create_seed_testcycle_testcases_testrun(step):
    step.behave_as("""
        Given I create the seed company and product with these names:
            | company name    | product name  |
            | Massive Dynamic | Cortexiphan   |
        When I create a new user with name "Capn Admin"
        and I activate the user with that name
        And I create a new role with name "Approvationalist" with the following permissions:
            | permissionCode               |
            | PERMISSION_TEST_CASE_EDIT    |
            | PERMISSION_TEST_CASE_APPROVE |
        And I add the role with name "Approvationalist" to the user with that name
        when the user with that name creates a new testcase with name "Check the Gizmo"
        and when I add these steps to the testcase with that name:
            | name      | stepNumber | estimatedTimeInMin | instruction    | expectedResult        |
            | Mockery   | 1          | 5                  | Go this way    | They went this way    |
            | Flockery  | 2          | 2                  | Go that way    | They went that way    |
            | Chockery  | 3          | 4                  | Go my way      | They went my way      |
            | Trockery  | 4          | 1                  | Go the highway | They went the highway |
            | Blockery  | 5          | 25                 | Just go away   | They went away        |
        Then when I create a new user with name "Joe Approver"
        and I activate the user with that name
        And I add the role with name "Approvationalist" to the user with that name
        and when the user with name "Joe Approver" approves the testcase with that name
        And when I create the following new testcycles:
            | name          | description               | product name | startDate  | endDate    | communityAuthoringAllowed | communityAccessAllowed |
            | Baroque Cycle | Ahh, the cycle of life... | Cortexiphan  | 2011/02/02 | 2012/02/02 | true                      | true                   |
        and when I create a new testrun with name "Running Man" with testcycle "Baroque Cycle"
    """)

@step('create the seed test')
def create_seed_test(step):
    step.given("create a new testsuite with name \"Capn Admin\"")



