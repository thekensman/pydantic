from typing import Any, Dict, Optional, Tuple, Type, TypeVar, Union
from typing_extensions import Literal

from pydantic import BaseConfig
from pydantic.class_validators import gather_all_validators
from pydantic.fields import SHAPE_FROZENSET, SHAPE_LIST, SHAPE_SEQUENCE, SHAPE_SET, SHAPE_TUPLE, FieldInfo
from pydantic.main import BaseModel, create_model

_null_types_cache: Dict[Tuple[Type[Any], Union[Any, Tuple[Any, ...]]], Type[BaseModel]] = {}
NullObjectT = TypeVar('NullObjectT', bound='NullObject')


class NoneLiteral(BaseModel):
    def none_validator(cls, data: Any):
        if data is not None:
            raise TypeError("Must be None. Instead got {value}".format(value=data))

        return data

    @classmethod
    def __get_validators__(cls):
        yield cls.none_validator


class EmptyListLiteral(BaseModel):
    def empty_list_validator(cls, data: Any):
        if data is not []:
            raise TypeError("Must be []. Instead got {value}".format(value=data))

        return data

    @classmethod
    def __get_validators__(cls):
        yield cls.empty_list_validator


def nullify_field(field):
    # TODO: Wait for literal values to be supported so we can do better checking: https://www.python.org/dev/peps/pep-0586/

    null_field_type, default_value = (
        # Null object
        (NullObject, nullify_field(field))
        if issubclass(field.type_, NullObject)
        else
        # Null list
        (EmptyListLiteral, [])
        if field.shape in (SHAPE_LIST, SHAPE_SET, SHAPE_FROZENSET, SHAPE_TUPLE, SHAPE_SEQUENCE)
        else
        # Null primitive or non-null object model
        (NoneLiteral, None)
    )

    return (
        null_field_type,
        FieldInfo(
            default=default_value,
            **{
                attribute: getattr(field.field_info, attribute, None)
                for attribute in field.field_info.__slots__
                if attribute not in ("default")
            },
        ),
    )


def create_null_object_model(
    model_name: str,
    *,
    __config__: Type[BaseConfig] = None,
    __base__: Type[BaseModel] = None,
    __module__: Optional[str] = None,
    __validators__: Dict[str, classmethod] = None,
    **field_definitions: Any,
) -> Type[BaseModel]:
    """
    Dynamically create a model.
    :param model_name: name of the created model
    :param __config__: config class to use for the new model
    :param __base__: base class for the new model to inherit from
    :param __validators__: a dict of method names and @validator class methods
    :param **field_definitions: fields of the model (or extra fields if a base is supplied) in the format
        `<name>=(<type>, <default default>)` or `<name>=<default value> eg. `foobar=(str, ...)` or `foobar=123`
    """
    null_fields = {
        field_name: nullify_field(field_definition) for field_name, field_definition in field_definitions.items()
    }

    null_model = Literal
    # create_model(
    #     model_name=model_name,
    #     __config__=__config__,
    #     __base__=__base__,
    #     __module__=__module__,
    #     __validators__=__validators__,
    #     **null_fields,
    # )
    # Don't allow partial construction of a null object
    # It must match entirely or it isn't valid
    # This prevents null objects from ever getting confused with valid objects
    # TODO: Is there a better way to set this during model creation?
    for field_name, field in null_model.__fields__.items():
        field.required = True

    return null_model


class NullObject(BaseModel):
    __slots__ = ()

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        #These none types should be replaced by the null object
        if kwargs in (None, {}):
            kwargs =

        return super().__new__(cls)

    def __class_getitem__(  # type: ignore
        # TODO: How can we verify that cls is a subclass of NullObject?
        cls: Any,
        param: NullObjectT,
    ) -> Type[BaseModel]:
        cached = _null_types_cache.get((cls, param))
        if cached is not None:
            return cached

        model_name = cls.__concrete_name__(param)
        validators = gather_all_validators(cls)

        null_object_model = create_null_object_model(
            model_name=model_name,
            __module__=cls.__module__,
            __base__=cls,
            __config__=None,
            __validators__=validators,
            **param.__fields__,
        )
        null_object_model.Config = cls.Config
        null_object_model.__concrete__ = True  # type: ignore
        _null_types_cache[(cls, param)] = null_object_model

        return Union[param, null_object_model]

    @classmethod
    def __concrete_name__(cls: Type[Any], param: Tuple[Type[Any], ...]) -> str:
        """
        This method can be overridden to achieve a custom naming scheme for GenericModels
        """
        param_name = getattr(param, "__name__", None) or str(param)
        return f'{cls.__name__}.{param_name}'


