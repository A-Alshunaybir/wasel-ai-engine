from pydantic import BaseModel

class UserComment(BaseModel):
    Event_Id: str
    User_Id: str
    User_Name: str
    Comment_Text: str
    Rating: float
    crowd_report: int

class TourRequest(BaseModel):
    user_lat: float
    user_lng: float
    available_hours: float
    preferences: str
    start_time: str