from pydantic import BaseModel
from typing import Dict, Optional

class Claim(BaseModel):
    user: str

class ClaimsDB:
    def __init__(self):
        self.claims: Dict[int, Claim] = {}
        self.next_claim_id: int = 1
    
    def cr_claim(self, _user: str) -> Claim:
        claim_id = self.next_claim_id
        self.next_claim_id += 1
        new_claim = Claim(
            user=_user
        )
        self.claims[claim_id] = new_claim
        return new_claim
    
    def get_claim(self, claim_id: int) -> Optional[Claim]:
        return self.claims.get(claim_id)
        
claims_db = ClaimsDB()
nw = claims_db.cr_claim("hello")
print(claims_db.get_claim(2))
if not claims_db.get_claim(2):
    print("huhu")