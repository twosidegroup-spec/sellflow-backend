from pydantic import BaseModel, EmailStr, Field, ConfigDict

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    business_name: str | None = Field(default=None, min_length=1, max_length=255)
    password: str = Field(min_length=4, max_length=64)
    # Optional fields for UI completeness (stored for future payment integration)
    payment_provider: str | None = Field(default=None, max_length=20)
    receiving_number: str | None = Field(default=None, max_length=50)
    # Required only when the server has REGISTRATION_INVITE_CODE configured.
    invite_code: str | None = Field(default=None, max_length=200)

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)

class BusinessBrief(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)

class UserRead(BaseModel):
    id: int
    email: str
    full_name: str
    phone: str | None = None
    payment_provider: str | None = None
    receiving_number: str | None = None
    business: BusinessBrief | None = None
    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    payment_provider: str | None = Field(default=None, max_length=20)
    receiving_number: str | None = Field(default=None, max_length=50)

class PasscodeChange(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=4, max_length=64)

class RegisterResponse(UserRead):
    business_id: int | None = None
    business_name: str | None = None

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
