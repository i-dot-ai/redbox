from fastapi import FastAPI


class SubApp:
    def __init__(self, router):
        self.app = FastAPI()
        self.router = router

        self.app.include_router(self.router)
