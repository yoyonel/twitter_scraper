# Note copied from http://python-jsonschema.readthedocs.io/en/latest/faq/

from jsonschema.validators import (
    Draft4Validator, extend
)


def extend_with_default(validator_class):
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        for prop, subschema in iter(properties.items()):
            if "default" in subschema:
                instance.setdefault(prop, subschema["default"])

        for error in validate_properties(
                validator, properties, instance, schema,
        ):
            yield error

    return extend(validator_class, {"properties": set_defaults})


def extend_with_no_checks_for_required(validator_class):
    def no_checks(_validator, _properties, _instance, _schema):
        return

    return extend(validator_class, {"required": no_checks})


PartialUpdateDraft4Validator = extend_with_no_checks_for_required(Draft4Validator)

DefaultValidatingDraft4Validator = extend_with_default(Draft4Validator)
