from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Literal
from datetime import datetime
from bson import ObjectId

# Custom ObjectId class to work with PyMongo
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


# Base User Model
class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    role: Literal["doctor", "patient", "guest"] = "guest"

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


# Model for creating a user
class UserCreate(UserBase):
    password: str

    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


# Model for user login
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# Patient specific model
class PatientModel(UserBase):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    assigned_doctor_id: Optional[str] = None
    dosha_result: Optional[str] = None
    allergies: List[str] = []
    approved_can_eat: List[str] = []
    approved_cannot_eat: List[str] = []
    role: Literal["patient"] = "patient"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# Doctor specific model
class DoctorModel(UserBase):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    role: Literal["doctor"] = "doctor"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# User response model
class UserResponse(BaseModel):
    id: str = Field(alias="_id")
    email: EmailStr
    first_name: str
    last_name: str
    role: str
    assigned_doctor_id: Optional[str] = None
    dosha_result: Optional[str] = None
    allergies: List[str] = []
    approved_can_eat: List[str] = []
    approved_cannot_eat: List[str] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


# Token model
class Token(BaseModel):
    access_token: str
    token_type: str


# Token data model
class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None
