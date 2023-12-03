# from pydantic import BaseModel, Field
from typing import Dict, List, Optional

import time

from .model import Claim, Status


class ClaimsDatabase:
    def __init__(self):
        self.claims: Dict[int, Claim] = {}
        self.next_claim_id: int = 1  # Start with 1, increment for each new claim

    def create_claim(
        self,
        prep_CID: str,
        user_address: str,
        timestamp_of_claim: str,
        comp_proof: str,
        comp_CID: str,
        value: int,
    ) -> Claim:
        """
        Creates a new claim and adds it to the database.
        """
        claim_id = self.next_claim_id
        self.next_claim_id += 1

        new_claim = Claim(
            user_address=user_address,
            disputing_user_address=None,
            timestamp_of_claim=timestamp_of_claim,
            status=Status.OPEN,
            collateral=value,
            compProof=comp_proof,
            compCID=comp_CID,
            prepCID=prep_CID,
            lastUpdated=int(time.time()),
        )
        self.claims[claim_id] = new_claim  # Using numerical ID
        return new_claim

    def get_next_claim_id(self) -> int:
        """
        Returns the ID that will be assigned to the next created claim.
        """
        return self.next_claim_id

    def initiate_dispute(
        self, claim_id: int, disputing_user_address: str
    ) -> Optional[Claim]:
        """
        Initiates a dispute on a specific claim.
        """
        claim = self.claims.get(claim_id)
        if claim:
            claim.disputing_user_address = disputing_user_address
            claim.status = Status.DISPUTING
            claim.lastUpdated = int(time.time())
            return claim
        return None

    def finalize_claim(self, claim_id: int, final_status: Status) -> Optional[Claim]:
        """
        Finalizes a claim with a given status.
        """
        claim = self.claims.get(claim_id)
        if claim:
            claim.status = final_status
            claim.lastUpdated = int(time.time())
            return claim
        return None
    
    def validate_or_contradict_claim(self, claim_id: int, claim_status: Status) -> Optional[Claim]:
        claim = self.claims.get(claim_id)
        if claim:
            claim.status = claim_status
            claim.lastUpdated = int(time.time())
            return claim
        return None
    
    def get_claim(self, claim_id: int) -> Optional[Claim]:
        """
        Retrieves a claim by its ID.
        """
        return self.claims.get(claim_id)

    def get_claim_by_prep_CID(self, prep_CID: str) -> Optional[Claim]:
        """
        Retrieves a claim by its prep_CID.
        """
        for claim in self.claims.values():
            if claim.prepCID == prep_CID:
                return claim
        return None

    def get_all_claims(self) -> List[Claim]:
        """
        Retrieves all claims in the database.
        """
        return list(self.claims.values())

    # Additional methods can be added as needed for your application


claims_db = ClaimsDatabase()
