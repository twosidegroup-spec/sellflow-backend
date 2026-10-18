from pydantic import BaseModel, EmailStr, Field, ConfigDict

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    business_name: str | None = Field(default=None, min_length=1, max_length=255)
    # Passcode-based auth (4 or 6 digits). Rate limiting on /auth/login protects against brute force.
    password: str = Field(min_length=4, max_length=64)

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)

class UserRead(BaseModel):
    id: int
    email: str
    full_name: str
    model_config = ConfigDict(from_attributes=True)

class RegisterResponse(UserRead):
    business_id: int | None = None
    business_name: str | None = None

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
