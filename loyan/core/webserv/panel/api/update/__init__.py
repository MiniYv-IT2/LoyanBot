"""本体更新接口 — check / apply / changelog"""


def register_routes(app) -> None:
    @app.route("/api/loyanui/update/check")
    async def update_check():
        from graci import check_update
        try:
            result = await check_update()
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "message": str(e)}, 400

    @app.route("/api/loyanui/update/apply", methods=["POST"])
    async def update_apply():
        from graci import apply_update
        try:
            result = await apply_update()
            return {"success": result.get("success", False), "data": result}
        except Exception as e:
            return {"success": False, "message": str(e)}, 400

    @app.route("/api/loyanui/update/changelog")
    async def update_changelog():
        from graci import get_update_log
        return {"success": True, "data": get_update_log()}
