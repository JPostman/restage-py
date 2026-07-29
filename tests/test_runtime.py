import unittest

from restage_py import (
    Collection,
    DependencyCycleError,
    HttpResponse,
    ReStage,
    RegistrationError,
    MockExecutor,
    RequestSpec,
    VerificationError,
)


class RuntimeTests(unittest.TestCase):
    def make_collection(self):
        return Collection(
            [
                RequestSpec("Login", "POST", "/login", "demo", "Auth"),
                RequestSpec("Current user", "GET", "/me", "demo", "Auth"),
            ]
        )

    def test_dependency_order_and_scope_inheritance(self):
        restage = ReStage()
        executor = MockExecutor(lambda request: HttpResponse(200, {"name": request.name}))

        @restage.request(id="login", namespace="demo", folder="Auth", request="Login")
        def login(ctx):
            ctx.request.body = {"username": "david"}

        @restage.response(id="me", depends_on="#login", request="Current user", verify=200)
        def current_user(ctx):
            self.assertEqual("Login", ctx.dependency("#login").response.body["name"])

        @restage.runner(depends_on="#me")
        def flow(ctx):
            return "done"

        runtime = restage.runtime(self.make_collection(), executor)
        result = runtime.run("flow")

        self.assertEqual("done", result.value)
        self.assertEqual(["#login", "#me", "flow"], runtime.execution_order)
        self.assertEqual(["Login", "Current user"], [call.name for call in executor.calls])

    def test_hard_verify_happens_before_body(self):
        restage = ReStage()
        body_called = False

        @restage.response(namespace="demo", folder="Auth", request="Current user", verify=200)
        def current_user(ctx):
            nonlocal body_called
            body_called = True

        runtime = restage.runtime(
            self.make_collection(),
            MockExecutor(lambda request: HttpResponse(500)),
        )
        with self.assertRaises(VerificationError):
            runtime.run("current_user")
        self.assertFalse(body_called)

    def test_soft_verify_happens_after_body(self):
        restage = ReStage()
        body_called = False

        @restage.response(
            namespace="demo",
            folder="Auth",
            request="Current user",
            verify=200,
            soft=True,
        )
        def current_user(ctx):
            nonlocal body_called
            body_called = True

        runtime = restage.runtime(
            self.make_collection(),
            MockExecutor(lambda request: HttpResponse(500)),
        )
        with self.assertRaises(VerificationError):
            runtime.run("current_user")
        self.assertTrue(body_called)

    def test_soft_assertions_are_aggregated(self):
        restage = ReStage()

        @restage.response(namespace="demo", folder="Auth", request="Current user")
        def current_user(ctx):
            soft = ctx.asserts.soft()
            soft.status_code(201)
            soft.is_true(False, "custom failure")

        runtime = restage.runtime(
            self.make_collection(),
            MockExecutor(lambda request: HttpResponse(200)),
        )
        with self.assertRaisesRegex(VerificationError, "custom failure"):
            runtime.run("current_user")

    def test_cycle_detection(self):
        restage = ReStage()

        @restage.runner(depends_on="second")
        def first(ctx):
            pass

        @restage.runner(depends_on="first")
        def second(ctx):
            pass

        runtime = restage.runtime(Collection(), MockExecutor(lambda request: HttpResponse(200)))
        with self.assertRaises(DependencyCycleError):
            runtime.run("first")

    def test_shared_dependency_executes_once_per_session(self):
        restage = ReStage()
        executor = MockExecutor(lambda request: HttpResponse(200))

        @restage.request(id="shared", namespace="demo", folder="Auth", request="Login")
        def shared(ctx):
            pass

        @restage.response(id="response", depends_on="#shared", request="Current user")
        def response(ctx):
            pass

        @restage.runner(id="runner", depends_on="#shared")
        def runner(ctx):
            pass

        @restage.runner(depends_on=("#response", "#runner"))
        def complete(ctx):
            pass

        runtime = restage.runtime(self.make_collection(), executor)
        runtime.run("complete")
        self.assertEqual(["Login", "Current user"], [call.name for call in executor.calls])

    def test_duplicate_id_is_rejected(self):
        restage = ReStage()

        @restage.runner(id="same")
        def first(ctx):
            pass

        with self.assertRaises(RegistrationError):
            @restage.runner(id="same")
            def second(ctx):
                pass


if __name__ == "__main__":
    unittest.main()
