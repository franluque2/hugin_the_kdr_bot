from core.kdr_data import KdrModifierNames, KDR_MODIFIERS

def parse_modifiers(modifier_string: str):
    # Split the string by commas, and strip whitespace
    modifiers = [mod.strip() for mod in modifier_string.split(',')]

    modifier_dict = {}
    
    for mod in modifiers:
        # Ensure we only split on the first '=' to avoid splitting inside values
        if '=' in mod:
            key, value = mod.split('=', 1)
            key = key.strip().lower()  # Normalize to lowercase
            value = value.strip()
            modifier_dict[key] = value
        else:
            # Otherwise, just add the modifier (without a value)
            mod = mod.strip().lower()
            modifier_dict[mod] = None

    return modifier_dict

def get_modifier(modifier_string: str, modifier: str):
    if not isinstance(modifier_string, str):
        return None
    # Parse the modifier string
    modifiers = parse_modifiers(modifier_string)
    
    # Convert the input modifier to lowercase for case-insensitive matching
    modifier = modifier.lower()

    # Check if the modifier exists in the parsed list
    print(modifiers)
    if modifier in modifiers:
        # Check if the modifier is expected to have a value
        print(modifier)
        if KDR_MODIFIERS.get(modifier, False):
            # Return the value if it has one
            print(modifiers[modifier])
            return modifiers[modifier]
        else:
            # Return True indicating the modifier exists but no value expected
            return True
    return None
