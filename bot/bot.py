from sc2.bot_ai import BotAI, Race
from sc2.data import Result
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId
from sc2.ids.upgrade_id import UpgradeId

class FourGateStrategy(BotAI):
    NAME: str = "FourGateStrategy"
    RACE: Race = Race.Protoss
    SUPPLY_LEFT_THRESHOLD = 2
    MAX_WORKERS = 22
    MAX_GATEWAYS = 4
    CHRONOBOOST_ENERGY_COST = 50

    def __init__(self):
        super().__init__()
        self.gateways_issued = 0  # Temporary Fix (Issues with Gateway-Limit)

    async def on_start(self):
        print("Game started")

    async def on_step(self, iteration: int):
        if not self.townhalls.ready:
            self.attack_with_workers()
            return

        nexus = self.townhalls.ready.random

        await self.distribute_workers()
        await self.build_workers(nexus)
        await self.build_pylons(nexus)
        await self.build_initial_gateway()
        await self.build_gas()
        await self.build_cyber_core()
        await self.build_additional_gateways()
        await self.train_stalkers()
        await self.chrono_boost(nexus)
        await self.research_warpgate()
        await self.attack()

    def attack_with_workers(self):
        for worker in self.workers:
            worker.attack(self.enemy_start_locations[0])

    async def build_workers(self, nexus):
        if self.workers.amount < self.townhalls.amount * self.MAX_WORKERS and nexus.is_idle and self.can_afford(UnitTypeId.PROBE):
            nexus.train(UnitTypeId.PROBE)

    async def build_pylons(self, nexus):
        if self.supply_left < self.SUPPLY_LEFT_THRESHOLD and self.can_afford(UnitTypeId.PYLON) and not self.already_pending(UnitTypeId.PYLON):
            pos = nexus.position.towards(self.enemy_start_locations[0], 10)
            await self.build(UnitTypeId.PYLON, near=pos)

    async def build_initial_gateway(self):
        if self.gateways_issued < 1 and self.can_afford(UnitTypeId.GATEWAY) and self.structures(UnitTypeId.PYLON).ready:
            pylon = self.structures(UnitTypeId.PYLON).ready.random
            await self.build(UnitTypeId.GATEWAY, near=pylon)
            self.gateways_issued += 1

    async def build_gas(self):
        if self.structures(UnitTypeId.GATEWAY):
            for nexus in self.townhalls.ready:
                vgs = self.vespene_geyser.closer_than(15, nexus)
                for vg in vgs:
                    if not self.can_afford(UnitTypeId.ASSIMILATOR):
                        break
                    worker = self.select_build_worker(vg.position)
                    if worker is None:
                        break
                    if not self.gas_buildings or not self.gas_buildings.closer_than(1, vg):
                        worker.build(UnitTypeId.ASSIMILATOR, vg)
                        worker.stop(queue=True)

    async def build_cyber_core(self):
        if self.can_afford(UnitTypeId.CYBERNETICSCORE) and self.structures(UnitTypeId.PYLON).ready and self.structures(UnitTypeId.GATEWAY).ready:
            pylon = self.structures(UnitTypeId.PYLON).ready.random
            if not self.structures(UnitTypeId.CYBERNETICSCORE) and self.already_pending(UnitTypeId.CYBERNETICSCORE) == 0:
                await self.build(UnitTypeId.CYBERNETICSCORE, near=pylon)

    async def train_stalkers(self):
        for gateway in self.structures(UnitTypeId.GATEWAY).ready:
            if self.can_afford(UnitTypeId.STALKER) and gateway.is_idle:
                gateway.train(UnitTypeId.STALKER)

    async def build_additional_gateways(self):
        # For Debug Purposes of Gateway Count
        # total_gateways = self.structures(UnitTypeId.GATEWAY).amount + self.already_pending(UnitTypeId.GATEWAY)
        # logging.debug(f'Total Gateways: {total_gateways}, Completed: {self.structures(UnitTypeId.GATEWAY).amount}, Pending: {self.already_pending(UnitTypeId.GATEWAY)}')

        if self.can_afford(UnitTypeId.GATEWAY) and self.structures(UnitTypeId.PYLON).ready and self.gateways_issued < 4:
            cyber_core_built = self.structures(UnitTypeId.CYBERNETICSCORE).ready.exists
            gas_built = self.structures(UnitTypeId.ASSIMILATOR).ready.exists

            if (cyber_core_built and gas_built):
                pylon = self.structures(UnitTypeId.PYLON).ready.random
                await self.build(UnitTypeId.GATEWAY, near=pylon)
                self.gateways_issued += 1

    async def chrono_boost(self, nexus):
        if not self.structures(UnitTypeId.CYBERNETICSCORE).ready:
            if not nexus.has_buff(BuffId.CHRONOBOOSTENERGYCOST) and not nexus.is_idle:
                if nexus.energy >= 50:
                    nexus(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, nexus)
        else:
            ccore = self.structures(UnitTypeId.CYBERNETICSCORE).ready.first
            if not ccore.has_buff(BuffId.CHRONOBOOSTENERGYCOST) and not ccore.is_idle:
                if nexus.energy >= 50:
                    nexus(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, ccore)

    async def research_warpgate(self):
        if self.can_afford(AbilityId.RESEARCH_WARPGATE) and self.structures(UnitTypeId.CYBERNETICSCORE).ready and self.already_pending_upgrade(UpgradeId.WARPGATERESEARCH) == 0:
            cyber_core = self.structures(UnitTypeId.CYBERNETICSCORE).ready.first
            cyber_core.research(UpgradeId.WARPGATERESEARCH)

    async def attack(self):
        stalkers = self.units(UnitTypeId.STALKER).ready.idle
        if stalkers.amount > 4:
            for stalker in stalkers:
                stalker.attack(self.enemy_start_locations[0])

    async def on_end(self, result: Result):
        print("Game ended.")