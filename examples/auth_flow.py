from restage_py import Collection, HttpResponse, ReStage, MockExecutor, RequestSpec

restage = ReStage()

collection = Collection(
    [
        RequestSpec(
            namespace="product",
            folder="Auth",
            name="Login user and get tokens",
            method="POST",
            url="https://example.test/auth/login",
            body={"username": "demo", "password": "demo"},
        ),
        RequestSpec(
            namespace="product",
            folder="Auth",
            name="Get current authenticated user",
            method="GET",
            url="https://example.test/auth/me",
        ),
    ]
)


def mock_handler(request: RequestSpec) -> HttpResponse:
    if request.name == "Login user and get tokens":
        return HttpResponse(200, {"accessToken": "token-123"})
    if request.name == "Get current authenticated user":
        return HttpResponse(200, {"username": "demo", "role": "admin"})
    return HttpResponse(404, {"error": "not found"})


executor = MockExecutor(mock_handler)


@restage.request(
    id="login",
    namespace="product",
    folder="Auth",
    request="Login user and get tokens",
)
def login(ctx):
    ctx.request.body["username"] = "python-user"


@restage.response(
    id="Ref1",
    depends_on="#login",
    request="Get current authenticated user",
    verify=200,
)
def get_current_user(ctx):
    token = ctx.dependency("#login").response.body["accessToken"]
    ctx.variables["accessToken"] = token
    ctx.asserts.status_code(200)


@restage.runner(id="authFlow", depends_on="#Ref1")
def authenticated_flow(ctx):
    assert ctx.variables["accessToken"] == "token-123"
    return "flow complete"


runtime = restage.runtime(collection, executor, session=True)


if __name__ == "__main__":
    result = runtime.run("#authFlow")
    print(result.value)
    print(runtime.execution_order)
