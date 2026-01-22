"""Discovery agent responsible for finding journalists' contact information.

The discovery agent uses a search client to query public sources based on
input prospect data. It returns a :class:`~pr_swarm.schemas.models.JournalistProfile`
containing any matched details. If data cannot be verified, fields are set
to ``"N/A"`` as per the Data Not Found policy. All exceptions are
propagated to the orchestrator, which handles retries and error logging.
"""

from __future__ import annotations

import logging
from typing import Optional

from ..schemas.models import JournalistProfile, Prospect
from ..utils.retry import retry_async
from ..utils.search_client import BaseSearchClient


class DiscoveryAgent:
    """Agent that discovers journalist details from public sources."""

    def __init__(self, search_client: BaseSearchClient, logger: Optional[logging.Logger] = None):
        self.search_client = search_client
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    async def run(self, prospect: Prospect) -> JournalistProfile:
        """Look up the journalist associated with a prospect.

        Parameters
        ----------
        prospect: Prospect
            The prospect information from the input CSV.

        Returns
        -------
        JournalistProfile
            A pydantic model with the discovered data.
        """
        self.logger.debug(f"Starting discovery for {prospect.name}")
        profile = await retry_async(self.search_client.search_journalist, prospect)
        self.logger.debug(
            f"Discovery completed for {prospect.name}: matched_name={profile.matched_name}, email={profile.email}"
        )
        return profile