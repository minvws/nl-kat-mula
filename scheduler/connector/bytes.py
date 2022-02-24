from .service import HTTPService


class Bytes(HTTPService):
    name = "bytes"

    user: str
    password: str
    token: str

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        self.password = kwargs.pop("password")

        super().__init__(*args, **kwargs)

        self.token = self._get_token(
            user=self.user,
            password=self.password,
        )

        self.headers.update({"Authorization": f"Bearer {self.token}"})

    def _get_token(self, user: str, password: str) -> str:
        url = f"{self.host}/token"
        response = self.post(
            url=url,
            payload={"username": user, "password": password},
            headers={"Content-Type": "application/x-www-form-urlendcoded"},
        )
        return response.json()["access_token"]
