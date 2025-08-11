from module.config.stored.classes import (
    StoredBase,
    StoredCounter,
    StoredDailyQuestFeedCounter,
    StoredDailyQuestRestockCounter,
    StoredInt,
    StoredItemContainer,
    StoredShopWizardRequests,
)


# This file was auto-generated, do not modify it manually. To generate:
# ``` python -m module/config/config_updater.py ```

class StoredGenerated:
    ShopWizardRequests = StoredShopWizardRequests("ShopWizard.ShopWizard.ShopWizardRequests")
    DailyQuestRestockTimesLeft = StoredDailyQuestRestockCounter("InventoryTool.PlayerStorage.DailyQuestRestockTimesLeft")
    DailyQuestFeedTimesLeft = StoredDailyQuestFeedCounter("InventoryTool.PlayerStorage.DailyQuestFeedTimesLeft")
    InventoryData = StoredItemContainer("InventoryTool.PlayerStorage.InventoryData")
    StockData = StoredItemContainer("InventoryTool.PlayerStorage.StockData")
    DepositData = StoredItemContainer("InventoryTool.PlayerStorage.DepositData")
