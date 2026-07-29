"""Runner and Response can independently depend on the same node."""

from restage_py import Collection, HttpResponse, ReStage, MockExecutor, RequestSpec

restage = ReStage()
collection = Collection(
    [
        RequestSpec("Shared setup", "POST", "https://example.test/setup", "demo", "Shared"),
        RequestSpec("Read result", "GET", "https://example.test/result", "demo", "Shared"),
    ]
)
executor = MockExecutor(lambda request: HttpResponse(200, {"request": request.name}))


@restage.request(
    id="shared",
    namespace="demo",
    folder="Shared",
    request="Shared setup",
)
def shared_setup(ctx):
    pass


@restage.response(
    id="responseRef",
    depends_on="#shared",
    request="Read result",
    verify=200,
)
def response_using_shared(ctx):
    pass


@restage.runner(id="runnerRef", depends_on="#shared")
def runner_using_shared(ctx):
    pass


runtime = restage.runtime(collection, executor)
