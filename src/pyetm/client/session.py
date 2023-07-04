"""Base methods and client"""
from __future__ import annotations
from typing import Literal

import os
import re
import copy
import functools

from urllib.parse import urljoin

import pandas as pd

from pyetm.logger import get_modulelogger
from pyetm.sessions import RequestsSession, AIOHTTPSession

# get modulelogger
logger = get_modulelogger(__name__)

SCOPE = Literal['public', 'read', 'write', 'delete']


class SessionMethods:
    """Core methods for API interaction"""

    @property
    def _default_engine_url(self) -> str:
        """default engine url"""
        return "https://engine.energytransitionmodel.com/api/v3/"

    @property
    def connected_to_default_engine(self) -> bool:
        """connected to default engine url?"""
        return self.engine_url == self._default_engine_url

    @property
    def _scenario_header(self) -> dict:
        """get full scenario header"""
        return self._get_scenario_header()

    @property
    def engine_url(self) -> str:
        """engine URL"""
        return self._engine_url

    @engine_url.setter
    def engine_url(self, url: str | None):

        # default url
        if url is None:
            url = self._default_engine_url

        # set engine
        self._engine_url = str(url)

        # reset token and change base url
        self.token = None
        self.session.base_url = self._engine_url

        # reset cache
        self._reset_cache()

    @property
    def etm_url(self) -> str:
        """model URL"""

        # raise error
        if self.etm_url is None:
            raise ValueError("ETModel URL not set on initialisation.")

        return self._etm_url

    @etm_url.setter
    def etm_url(self, url: str | None):

        # use default pro location
        if (url is None) & (self.connected_to_default_engine):
            url = "https://energytransitionmodel.com/"

        # set etmodel
        self._etm_url = str(url)

    @property
    def scenario_id(self) -> int | None:
        """scenario id"""
        return self._scenario_id if hasattr(self, '_scenario_id') else None

    @scenario_id.setter
    def scenario_id(self, scenario_id: int | None):

        # store previous scenario id
        previous = copy.deepcopy(self.scenario_id)

        # try accessing dict
        if isinstance(scenario_id, dict):
            scenario_id = scenario_id['id']

        # convert passed id to integer
        if scenario_id is not None:
            scenario_id = int(scenario_id)

        # set new scenario id
        self._scenario_id = scenario_id

        # log changed scenario id
        if self.scenario_id != previous:
            logger.debug(f"Updated scenario_id: '{self.scenario_id}'")

        # reset session
        if self.scenario_id != previous:
            self._reset_cache()

        # validate scenario id
        self._get_scenario_header()

    @property
    def token(self) -> pd.Series | None:
        """optional personal access token for authorized use"""

        # return None without token
        if self._token is None:
            return None

        # make request
        url = '/oauth/token/info'
        headers = {'content-type': 'application/json'}

        # get token information
        resp: dict = self.session.get(
            url, decoder='json', headers=headers)

        # convert utc timestamps
        resp['created_at'] = pd.to_datetime(resp['created_at'], unit='s')
        resp['expires_in'] = pd.Timedelta(resp['expires_in'], unit='s')

        return pd.Series(resp, name='token')

    @token.setter
    def token(self, token: str | None = None):

        # check environment variables for token
        if token is None:
            token = os.getenv('ETM_ACCESS_TOKEN')

        # store token
        self._token = token

        # update persistent session headers
        if self._token is None:

            # pop authorization if present
            if 'Authorization' in self.session.headers.keys():
                self.session.headers.pop('Authorization')

        else:

            # set authorization
            authorization = {'Authorization': f'Bearer {self._token}'}
            self.session.headers.update(authorization)

    @property
    def user(self) -> pd.Series:
        """info about token owner if token assigned"""

        # validate token permission
        self._validate_token_permission('openid')

        # make request
        url = '/oauth/userinfo'
        headers = {'content-type': 'application/json'}

        # get token information
        resp: dict = self.session.get(
            url, decoder='json', headers=headers)

        return pd.Series(resp, name='user')

    @property
    def session(self) -> RequestsSession | AIOHTTPSession:
        """session object that handles requests"""
        return self._session if hasattr(self, '_session') else None

    @functools.lru_cache(maxsize=1)
    def _get_scenario_header(self):
        """get header of scenario"""

        # return no values
        if self.scenario_id is None:
            return {}

        # raise without scenario id
        self._validate_scenario_id()

        # make request
        url = f'scenarios/{self.scenario_id}'
        header = self.session.get(url)

        return header

    def _get_session_id(self, scenario_id: int) -> int:
        """get a session_id for a pro-environment scenario"""

        # extract content from url
        url = urljoin(self.etm_url, f'saved_scenarios/{scenario_id}/load/')
        content = self.session.request("get", url, decoder='text')

        # get session id from content
        pattern = '"api_session_id":([0-9]{6,7})'
        session_id = re.search(pattern, content)

        return int(session_id.group(1))

    def _validate_scenario_id(self):
        """raise error when scenario id is None"""

        # check if scenario id is None
        if self.scenario_id is None:
            raise ValueError('scenario id is None')

    def _validate_token_permission(self, scope: SCOPE = 'public'):
        """validate token permission"""

        # raise without token
        if self._token is None:
            raise ValueError("No personall access token asssigned")

        # check if scope is known
        if scope is None:
            raise ValueError(f"Unknown token scope: '{scope}'")

        if scope not in self.token.get('scope'):
            raise ValueError(f"Token has no '{scope}' permission.")

    def _reset_cache(self):
        """reset cached scenario properties"""

        # clear parameter caches
        self._get_scenario_header.cache_clear()

    def _update_scenario_header(self, header: dict):
        """change header of scenario"""

        # raise without scenario id
        self._validate_scenario_id()

        # set data
        data = {"scenario": header}
        url = f'scenarios/{self.scenario_id}'

        # make request
        self.session.put(url, json=data)

        # clear scenario header cache
        self._get_scenario_header.cache_clear()
