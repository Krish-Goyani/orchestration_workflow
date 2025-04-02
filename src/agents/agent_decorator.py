from typing import Any, Optional, Type

from src.models.schema.agent_schema import Agent


class AgentType(type):
    """
    Metaclass for agent classes that returns the schema when accessed directly
    """

    def __new__(mcs, name, bases, attrs):
        # Create the class as normal
        cls = super().__new__(mcs, name, bases, attrs)

        # Create and attach the schema
        schema = Agent(name=name, description=cls.__doc__ or "")
        cls._schema = schema

        return cls

    def __repr__(cls):
        # When the class is accessed directly, return the schema
        return repr(cls._schema)

    def __str__(cls):
        # When the class is accessed directly, return the schema
        return str(cls._schema)


def agent(_cls: Optional[Type] = None) -> Any:
    """
    Agent decorator that makes a class both instantiable and schema-returning.

    Usage:
        @agent
        class MyAgent:
            ...

        # Get schema by printing or displaying the class
        print(MyAgent)  # Shows Agent schema

        # Create instance
        agent_instance = MyAgent()
    """

    def wrap(cls: Type) -> Type:
        # Extract metadata
        name = cls.__name__
        description = cls.__doc__ or ""

        # Create schema
        schema_obj = Agent(name=name, description=description.strip())

        # Create a new class with AgentType metaclass
        new_attrs = dict(cls.__dict__)
        # Add schema as class attribute
        new_attrs["_schema"] = schema_obj

        # Create new class with metaclass
        agent_cls = AgentType(name, cls.__bases__, new_attrs)

        return agent_cls

    # Handle both @agent and @agent() usage
    if _cls is None:
        return wrap
    else:
        return wrap(_cls)
