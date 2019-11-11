from pydantic import BaseModel
from pydantic.null_object import  NullObject
from pydantic import ValidationError
import pytest

class Base(BaseModel):
    optional_type: str = None
    required_type: str = ...


# class NestedBase(BaseModel):
#     base: Base


class ModelTest(BaseModel):
    base: NullObject[Base]
    # nested_base: NullObject[NestedBase]


# WORKS
def test_valid_null_model():
    # Hits null model
    test = ModelTest(base={"optional_type": None, "required_type": None,})
    assert isinstance(test.base, NullObject[Base])
def test_valid_model():
    # Hits valid model
    test = ModelTest(base={"optional_type": None, "required_type": "test",})
    assert isinstance(test.base, Base)
    test = ModelTest(base={"required_type": "test",})
    assert isinstance(test.base, Base)

# DOESN'T WORK
def test_invalid_null_model():
    # Either a partial null object or a real object without the required type
    pytest.raises(ValidationError, ModelTest, base={"optional_type": None,})
def test_invalid_nodel():
    # A real object without the required type set
    pytest.raises(ValidationError, ModelTest, base={"optional_type": "test",})

# SHOULD WORK BUT DOESN'T
# def test_empty_model():
#     # Field is required by pydantic so never has a chance to populate null object
#     test = ModelTest()
#     assert isinstance(test.base, NullObject[Base])
# def test_none_model():
#     # None isn't registered as null object
#     test = ModelTest(base=None)
#     assert isinstance(test.base, NullObject[Base])
# def test_empty_dictionary_model():
#     # Intentionally empty object isn't registered as null object
#     test = ModelTest(base={})
#     assert isinstance(test.base, NullObject[Base])