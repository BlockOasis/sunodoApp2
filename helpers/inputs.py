from pydantic import BaseModel
from .setting import settings

# {"handle": "claim","cidPrep": "QmdsL7GxAPRbYh9U7mG6ctnjhbChC7Yws4oriSxUafQ41R","cidComp": "QmdsL7GxAPRbYh9U7mG6ctnjhbChC7Yws4oriSxUafQ41R","coll": "1000000000000000000","compProof": "QmdsL7GxAPRbYh9U7mG6ctnjhbChC7Yws4oriSxUa"}


class ClaimInput(BaseModel):
    handle: str = "claim"
    prep_CID: str
    comp_CID: str
    collateral: int
    computation_proof: str



class WithdrawInput(BaseModel):
    action: str = "withdraw"
    amount: int


"""
{
    "handle": "finalize",
    "claimID": 12345,
    "prep_CID": "QmExampleCID"
}
"""


class FinalizeInput(BaseModel):
    handle: str = "finalize"
    claimID: int
    prep_CID: str


class ValidateInput(BaseModel):
    handle: str = "validate"
    claimID: int
    preprocessed_data: str
    computation_proof: str

"""
Example Payload:
{
    "handle": "dispute",
    "claimID": "12345",
    "stakingAmount": "400000000000000000",
    "prep_CID": "QmExampleCID"
}
"""

class DisputeInput:
    handle: str = "dispute"
    claimID: int
    staking_amount: int = settings.VALIDATOR_STAKING
    prep_CID: str