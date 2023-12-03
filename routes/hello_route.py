from helpers.utils import str2hex, to_jsonhex
from cartesi import Rollup, RollupData

def register_hello(url_router, json_router):
    @url_router.advance("hello/")
    def hello_world_advance(rollup: Rollup, data: RollupData) -> bool:
        rollup.notice(str2hex("Hello World"))
        return True

    @url_router.inspect("hello/")
    def hello_world_inspect(rollup: Rollup, data: RollupData) -> bool:
        rollup.report(str2hex("Hello World-Jhingalalahuhu"))
        return True
    # {"hello": "world", "action": "reaction"}
    @json_router.advance({"hello": "world"})
    def handle_advance_set(rollup: Rollup, data: RollupData):
        data = data.json_payload()
        rollup.report(to_jsonhex({"action": data["action"]}))
        return True
