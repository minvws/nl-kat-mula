import datetime
import logging
import socket
import time
import urllib.parse
from typing import Any, Callable, Dict, List, Union

import requests


class HTTPService:
    """HTTPService exposes methods to make http requests to services that
    typically expose rest api endpoints

    Attributes:
        logger:
            The logger for the class.
        session:
            A requests.Session object.
        name:
            A string describing the name of the service. This is used args
            an identifier.
        source:
            As string defining the request user agent of HTTP request made from
            this HTTPService instance. This helps services differentiate from
            where the requests came from.
        host:
            A string url formatted reference to the host of the service
        headers:
            A dict containing the request headers.
        health_endpoint:
            A string defining the health endpoint for the service. Used too
            determine whether a host is healthy.
        timeout:
            An integer defining the timeout of requests.
    """

    name: str
    health_endpoint: Union[str, None] = "/health"

    def __init__(self, host: str, source: str, timeout: int = 5):
        """Initializer of the HTTPService class. During initialization thr
        host will be checked if it is available and healthy.

        Args:
            host:
                A string url formatted reference to the host of the service
            source:
                A string defining the request source of HTTP request made from
                this HTTPService instance. This helps services differentiate
                from where the requests came from.
            timeout:
                An integer defining the timeout of requests.
        """
        self.logger: logger.Logger = logging.getLogger(self.__class__.__name__)
        self.session = requests.Session()
        self.host = host
        self.timeout = timeout
        self.source = source

        self.headers: Dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        if self.source:
            self.headers["User-Agent"] = self.source


        self._do_checks()

    def get(
        self, url: str, payload: Dict[str, Any] = {}, headers: Dict[str, Any] = {}, params: Dict[str, Any] = {}
    ) -> requests.Response:
        """Execute a HTTP GET request

        Args:
            headers:
                A dict to set additional headers for the request.
            params:
                A dict to set the query paramaters for the request

        Returns:
            A request.Response object
        """
        response = self.session.get(
            url,
            headers=self.headers.update(headers) if headers else self.headers,
            params=params,
            data=payload,
            timeout=self.timeout,
        )
        self.logger.debug(f"Made GET request to {url}. [name={self.name}, url={url}]")

        self._verify_response(response)

        return response

    def post(
        self, url: str, payload: Dict[str, Any], headers: Dict[str, Any] = {}, params: Dict[str, Any] = {}
    ) -> requests.Response:
        """Execute a HTTP POST request

        Args:
            headers:
                A dict to set additional headers for the request.
            params:
                A dict to set the query paramaters for the request

        Returns:
            A request.Response object
        """
        response = self.session.post(
            url,
            headers=self.headers.update(headers) if headers else self.headers,
            params=params,
            data=payload,
            timeout=self.timeout,
        )
        self.logger.debug(f"Made POST request to {url}. [name={self.name}, url={url}, data={payload}]")

        self._verify_response(response)

        return response

    def _do_checks(self) -> None:
        """Do checks whether a host is available and healthy."""
        if self.host is not None and self._retry(self._is_host_available) is False:
            raise RuntimeError(f"Host {self.host} is not available.")

        if self.health_endpoint is not None and self._retry(self._is_host_healthy) is False:
            raise RuntimeError(f"Service {self.name} is not running.")

    def _is_host_available(self) -> bool:
        """Check if the host is available.

        Returns:
            A boolean
        """
        try:
            uri = urllib.parse.urlparse(self.host)
            if uri.netloc.find("@") != -1:
                host, port = uri.netloc.split("@")[1].split(":")
            else:
                host, port = uri.netloc.split(":")

            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, int(port)))
            return True
        except socket.error:
            return False

    def _is_host_healthy(self) -> bool:
        """Check if host is healthy by inspecting the host's health endpoint.

        Returns:
            A boolean
        """
        try:
            self.get(f"{self.host}{self.health_endpoint}")
            return True
        except requests.exceptions.RequestException:
            return False

    def _retry(self, func: Callable) -> bool:
        """Retry a function until it returns True.

        Args:
            func: A python callable that needs to be retried.

        Returns:
            A boolean signifying whether or not the func was executed successfully.
        """
        i = 0
        while i < 10:
            if func() is True:
                self.logger.info(f"Connected to {self.host}. [name={self.name}, host={self.host}, func={func.__name__}]")
                return True
            else:
                self.logger.warning(
                    f"Not able to reach host, retrying in {self.timeout} seconds. [name={self.name}, host={self.host}, func={func.__name__}]"
                )

                i += 1
                time.sleep(self.timeout)

        return False

    # FIXME: handle the exception, we don't want to stop threads because
    # of a bad response
    def _verify_response(self, response: requests.Response) -> None:
        """Verify the received response from a request.

        Raises:
            Exception
        """
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTPError: {str(e)} [name={self.name}, url={response.url}, response={response.content}]")
            raise (e)
