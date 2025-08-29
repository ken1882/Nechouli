from module.config.stored.classes import (
    StoredBase,
    StoredCounter,
    StoredDailyQuestFeedCounter,
    StoredDailyQuestRestockCounter,
    StoredInt,
    StoredItemContainer,
    StoredList,
    StoredPendingTrainingFee,
    StoredPetsData,
    StoredShopWizardRequests,
)


# This file was auto-generated, do not modify it manually. To generate:
# ``` python -m module/config/config_updater.py ```

class StoredGenerated:
    PendingTrainingFee = StoredPendingTrainingFee("PetTraining.PetTraining.PendingTrainingFee")
    DailyQuestRestockTimesLeft = StoredDailyQuestRestockCounter("DailyQuest.DailyQuest.DailyQuestRestockTimesLeft")
    DailyQuestFeedTimesLeft = StoredDailyQuestFeedCounter("DailyQuest.DailyQuest.DailyQuestFeedTimesLeft")
    ShopWizardRequests = StoredShopWizardRequests("ShopWizard.ShopWizard.ShopWizardRequests")
    EarnedPlotPoints = StoredInt("VoidsWithin.VoidsWithin.EarnedPlotPoints")
    NeoPoints = StoredInt("InventoryTool.PlayerStorage.NeoPoints")
    InventoryData = StoredItemContainer("InventoryTool.PlayerStorage.InventoryData")
    StockData = StoredItemContainer("InventoryTool.PlayerStorage.StockData")
    PetsData = StoredPetsData("InventoryTool.PlayerStorage.PetsData")
    DepositData = StoredItemContainer("SafetyDepositBox.SafetyDepositBox.DepositData")
