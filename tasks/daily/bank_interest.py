from module.logger import logger
from tasks.base.base_page import BasePageUI
from module.base.utils import str2int
from module.db.data_map import BANK_LEVEL_NAME, BANK_LEVEL_REQUIREMENT

class BankInterestUI(BasePageUI):

    def main(self):
        self.goto('https://www.neopets.com/bank.phtml')
        btn = self.page.locator('#frmCollectInterest')
        if btn.count():
            self.device.click(btn)
            self.device.wait(1)
        wallet = self.update_np()
        balance = str2int(self.page.locator('#txtCurrentBalance1').text_content())
        threshold = self.config.NeopianBank_DepositThreshold
        logger.info(f"Bank Balance: {balance}")
        if wallet < threshold:
            self.config.stored.Balance.set(balance)
            return True
        deposit = min(
            self.config.NeopianBank_DepositThreshold,
            (threshold - self.config.ProfileSettings_MinNpKeep) // 2
        )
        cur_level_name = self.page.locator('#txtAccountType').text_content().strip()
        cur_level = next((lvl for lvl, name in BANK_LEVEL_NAME.items() if name == cur_level_name), 1)
        fields = self.page.locator('input[name="amount"]')
        if fields.count() < 3:
            logger.error("Bank deposit fields not found")
            return True
        qualified = next(
            (lvl for lvl, req in reversed(BANK_LEVEL_REQUIREMENT.items()) if balance >= req),
            cur_level
        )
        self.page.on('dialog', lambda dialog: dialog.accept())
        result_txt = self.page.locator('#frmDepositResult')
        if qualified > cur_level:
            logger.info(
                f"Upgrading bank from {BANK_LEVEL_NAME[cur_level]} to {BANK_LEVEL_NAME[qualified]}\n"
                f"Depositing {deposit} NP"
            )
            deposit = BANK_LEVEL_REQUIREMENT[cur_level + 1] - balance
            acc_sel = self.page.locator('#account_type')
            acc_sel.select_option(value=str(cur_level + 1))
            fields.nth(2).fill(str(deposit))
            self.device.click('input[value="Change Account"]')
            result_txt = self.page.locator('#frmUpgradeAccountResult')
        else:
            logger.info(f"Depositing {deposit} NP")
            fields.nth(0).fill(str(deposit))
            self.device.click('input[value="Deposit"]')
        while True:
            self.device.wait(0.5)
            if not result_txt.is_visible():
                continue
            if len(result_txt.text_content()) < 10:
                continue
            break
        balance = str2int(self.page.locator('#txtCurrentBalance1').text_content())
        self.config.stored.Balance.set(balance)
        wallet = self.update_np()
        logger.info(f"New bank balance: {balance}, wallet: {wallet}")
        return True


if __name__ == '__main__':
    self = BankInterestUI()
