from enum import Enum


class FreeBoostType(str, Enum):
    TURBO = "Turbo"
    ENERGY = "Recharge"


class UpgradableBoostType(str, Enum):
    TAP = "Damage"
    ENERGY = "EnergyCap"
    CHARGE = "EnergyRechargeRate"
    TAPBOT = "TapBot"
