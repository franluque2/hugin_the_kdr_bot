from discord.app_commands import CheckFailure


class PlayerNotInInstanceError(CheckFailure):
    pass


class PlayerAlreadyJoinedError(CheckFailure):
    pass


class InstanceDoesNotExistError(CheckFailure):
    pass


class InstanceStartedError(CheckFailure):
    pass


class InstanceStartedError(CheckFailure):
    pass


class InstanceNotStartedError(CheckFailure):
    pass


class PlayerHasClassAlreadyError(CheckFailure):
    pass


class PlayerHasNoClassError(CheckFailure):
    pass


class PlayerNotInRoundError(CheckFailure):
    pass


class PlayerHasNoCharacterSheetError(CheckFailure):
    pass


class BuildDBDataError(CheckFailure):
    pass


class ServerNotWhitelistedError(CheckFailure):
    pass
