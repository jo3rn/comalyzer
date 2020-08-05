from colorama import Fore, init, Style
from datetime import date, datetime
import config
import zeep


class Manager:
    def __init__(self, manager_id, name):
        self.manager_id = manager_id
        self.name = name
        self.budget = config.INITIAL_BUDGET
        self.line_up = []
        self.history = []

    def change_budget(self, amount):
        self.budget += amount

    def buy_player(self, player):
        # add player to line up
        self.line_up += [player]
        # adjust manager's budget
        self.change_budget(-player.purchase_price)

    def sell_player(self, player_id, price, selling_date, buyer):
        # add player to manager's history
        player = next((x for x in self.line_up if x.player_id == player_id), None)
        self.history += [HistoryEntry(player, price, selling_date, buyer)]
        # remove player from line up
        self.line_up[:] = [x for x in self.line_up if not x.player_id == player_id]
        # adjust manager's budget
        self.change_budget(price)


class Player:
    def __init__(self, player_id, name, purchase_price, purchase_date):
        self.player_id = player_id
        self.name = name
        self.purchase_price = int(purchase_price)
        self.purchase_date = purchase_date
        self.current_value = -1

    def set_current_value(self, value):
        self.current_value = int(value)


class HistoryEntry:
    def __init__(self, player, selling_price, selling_date, buyer):
        self.player_id = player.player_id
        self.player_name = player.name
        self.purchase_price = player.purchase_price
        self.purchase_date = player.purchase_date
        self.selling_price = selling_price
        self.selling_date = selling_date
        self.sold_to = buyer


class NewsParser:
    PREFIX_PLAYER_ID = "<a href=\"../../bundesligaspieler/"
    CLOSING_ANGLE_BRACKET = ">"
    CLOSING_TAG_A = "</a"
    PREFIX_MANAGER_ID = "playerInfo.phtml?pid="

    player_id = -1
    player_name = ""
    seller = "Computer"
    seller_id = -1
    buyer = "Computer"
    buyer_id = -1
    price = -1
    entry_date = -1

    def extract_player_id(self, processed_string):
        self.player_id = processed_string

    def extract_player_name(self, processed_string):
        self.player_name = processed_string.replace(self.CLOSING_TAG_A, '')

    def extract_price(self, processed_string):
        self.price = int(processed_string.replace(".", ''))

    def extract_selling_manager(self, processed_string):
        self.seller = processed_string.split(self.CLOSING_ANGLE_BRACKET, 2)[1].replace(self.CLOSING_TAG_A, '')
        self.extract_selling_manager_id(processed_string)

    def extract_selling_manager_id(self, processed_string):
        self.seller_id = processed_string.split("\"", 2)[1].replace(self.PREFIX_MANAGER_ID, '')

    def extract_buying_manager_name(self, processed_string):
        self.buyer = processed_string.replace(self.CLOSING_TAG_A, '')

    def extract_buying_manager_id(self, processed_string):
        self.buyer_id = processed_string.split("\"")[0].replace(self.PREFIX_MANAGER_ID, '')

    @staticmethod
    def is_computer_in_string(processed_string):
        return processed_string[4:12] == "Computer"

    def parse_transfers(self, data):
        transfer_list = data.split(self.PREFIX_PLAYER_ID)
        for transfer in transfer_list:
            id_and_rest = transfer.split('-', 1)
            self.extract_player_id(id_and_rest[0])
            try:
                name_and_rest = id_and_rest[1].split(self.CLOSING_ANGLE_BRACKET, 2)[1:]
                self.extract_player_name(name_and_rest[0])
            except IndexError:
                continue

            price_and_rest = name_and_rest[1].split(" ", 4)[3:]
            self.extract_price(price_and_rest[0])
            seller_and_rest = price_and_rest[1]
            if self.is_computer_in_string(seller_and_rest):
                # player sold by computer
                buyer_and_rest = seller_and_rest.split("zu <a href=\"")[1].split(">", 2)
                self.extract_buying_manager_id(buyer_and_rest[0])
                self.extract_buying_manager_name(buyer_and_rest[1])
                if self.buyer_id not in dict_manager:
                    # add new manager to manager dictionary
                    manager = Manager(self.buyer_id, self.buyer)
                    dict_manager[self.buyer_id] = manager
                buying_manager = dict_manager[self.buyer_id]
                buying_manager.buy_player(Player(self.player_id, self.player_name, self.price, self.entry_date))
            else:
                # player sold by manager
                self.extract_selling_manager(seller_and_rest)
                if self.is_computer_in_string(seller_and_rest.split(">", 2)[2]):
                    # player sold to computer
                    self.buyer = "Computer"
                    self.buyer_id = -1
                else:
                    # player sold to manager
                    buyer_and_rest = seller_and_rest.split("zu <a href=\"")[1].split(">", 2)
                    self.extract_buying_manager_id(buyer_and_rest[0])
                    self.extract_buying_manager_name(buyer_and_rest[1])
                    buying_manager = dict_manager[self.buyer_id]
                    buying_manager.buy_player(Player(self.player_id, self.player_name, self.price, self.entry_date))
                selling_manager = dict_manager[self.seller_id]
                selling_manager.sell_player(self.player_id, self.price, self.entry_date, self.buyer)

    def start(self):
        print("Start parsing news...")
        with open("news_dump.txt", 'r', encoding='utf-8') as news_dump:
            for line in news_dump:
                try:
                    self.entry_date = datetime.strptime(line.rstrip(), '%Y-%m-%dT%H:%M:%S%z')
                except ValueError:
                    self.parse_transfers(line)
            print("News parsed.")


class NewsSaver:
    FIRST_LEVEL = "_value_1"

    def save_news(self, news_to_save):
        skip_count = 0
        save_count = 0
        print("Saving news to disk...")
        with open("news_dump.txt", 'a+', encoding='utf-8') as news_dump:
            for entry in reversed(news_to_save[self.FIRST_LEVEL]):
                data = entry[self.FIRST_LEVEL]
                if data[2] == "Transfers":
                    former_date = get_news_dump_date()
                    entry_date = data[0]
                    if entry_date > former_date:
                        save_count += 1
                        news_dump.write("\n" + entry_date)
                        news_dump.write("\n" + data[3])
                        set_news_dump_date(entry_date)
                    else:
                        skip_count += 1
            print("{} days of news saved. {} days of news skipped.\n".format(save_count, skip_count))


class SoapLoader:
    def __init__(self, soap_client):
        self.client = soap_client

    def load_news(self):
        try:
            news_dump_date = get_news_dump_date()
            days_since_last_update = abs(
                (date.today() - datetime.strptime(news_dump_date.rstrip(), '%Y-%m-%dT%H:%M:%S%z').date()).days)
        except ValueError:
            days_since_last_update = abs(
                (date.today() - date(config.SEASON_START_YEAR,
                                     config.SEASON_START_MONTH,
                                     config.SEASON_START_DAY)).days)
        if days_since_last_update > 0:
            print("Loading news of the last {} days...".format(days_since_last_update))
            with self.client.settings(strict=False):
                loaded_news = self.client.service.getcomputernews(config.COMMUNITY_ID,
                                                                  days_since_last_update,
                                                                  days_since_last_update * 2)
                print("News loaded.\n")
                news_saver.save_news(loaded_news)
        else:
            print("News already up to date.")

    def load_market_value_of_all_line_ups(self):
        print("Loading current market values...")
        count = 0
        with self.client.settings(strict=False):
            for manager in dict_manager.values():
                for player in manager.line_up:
                    count += 1
                    player.set_current_value(self.load_market_value_of_a_player(player.player_id))
            print("Current market value of {} player(s) loaded.".format(count))

    def load_market_value_of_a_player(self, player_id):
        with self.client.settings(strict=False):
            market_value = client.service.getquote(player_id, date.today())
        return market_value


def get_news_dump_date():
    with open("news_dump_date.txt", 'a+') as news_dump_date:
        news_dump_date.seek(0)
        return news_dump_date.readline()


def set_news_dump_date(new_dump_date):
    with open("news_dump_date.txt", 'a+') as news_dump_date:
        news_dump_date.truncate(0)
        news_dump_date.write(new_dump_date)


def print_summary():
    budgets = []
    for manager in dict_manager.values():
        print("### {} ".format(manager.name).ljust(59, '#'))

        print("".ljust(59, '#'))
        print_line_up(manager)
        print("".ljust(59, '#'))
        print_trade_history(manager.history)

        print("".ljust(59, '#'))
        print("\n")

        budgets.append((manager.name, manager.budget))

    # sort budgets by budget value
    budgets.sort(key=lambda x: x[1])
    print("\nBudget summary:")
    for (name, budget) in budgets:
        if budget < 0:
            budget_color = Fore.RED
        else:
            budget_color = Fore.GREEN
        print("# " + budget_color + "{:11,} ".format(budget) + Style.RESET_ALL + "(" + name + ")")


def print_line_up(manager):
    print("### LINE UP ".ljust(59, '#'))
    line_up_value = 0
    for player in manager.line_up:
        difference = player.current_value - player.purchase_price
        line_up_value += player.current_value
        if difference < 0:
            player_color = Fore.RED
        else:
            player_color = Fore.GREEN
        print("#" + player_color + u'{:11,} {:20} {:10,}'.format(player.current_value, player.name,
                                                                 difference) + Style.RESET_ALL + " ({:10,})".format(
            player.purchase_price))
    print("".ljust(59, '#'))
    print("#{:11,} total line up ".format(line_up_value, manager.budget))
    if manager.budget < 0:
        budget_color = Fore.RED
    else:
        budget_color = Fore.GREEN
    print("#" + budget_color + "{:11,}".format(manager.budget) + Style.RESET_ALL + " remaining budget ")
    diff_to_initial = -1 * (config.INITIAL_BUDGET - line_up_value - manager.budget)
    if diff_to_initial < 0:
        diff_color = Fore.RED
    else:
        diff_color = Fore.GREEN
    print("#" + diff_color + "{:11,}".format(diff_to_initial) + Style.RESET_ALL + " difference to initial budget ")


def print_trade_history(history):
    total_diff = 0
    highest_profit = 0
    highest_profit_name = ""
    highest_loss = 0
    highest_loss_name = ""
    print("### TRADES ".ljust(59, '#'))
    for entry in history:
        diff = entry.selling_price - entry.purchase_price
        total_diff += diff
        if diff > highest_profit:
            highest_profit = diff
            highest_profit_name = entry.player_name
        elif diff < highest_loss:
            highest_loss = diff
            highest_loss_name = entry.player_name
        if diff < 0:
            diff_color = Fore.RED
        else:
            diff_color = Fore.GREEN
        print("#" + diff_color + "{:11,}".format(diff) + Style.RESET_ALL +
              " {:20} {} to {}".format(entry.player_name, entry.selling_date.strftime("%d.%m.%y"), entry.sold_to))
    print("".ljust(59, '#'))
    if total_diff < 0:
        print("#" + Fore.RED + "{:11,}".format(total_diff) + Style.RESET_ALL + " total in trading")
    else:
        print("#" + Fore.GREEN + "{:11,}".format(total_diff) + Style.RESET_ALL + " total in trading")
    print("#" + Fore.GREEN + "{:11,}".format(highest_profit) + Style.RESET_ALL + " highest profit with {}".format(
        highest_profit_name))
    print("#" + Fore.RED + "{:11,}".format(highest_loss) + Style.RESET_ALL + " highest loss with {}".format(
        highest_loss_name))


if __name__ == "__main__":
    # initialize colorama (colored console output) https://pypi.org/project/colorama/
    init(autoreset=True)

    # instantiate stuff
    dict_manager = {}
    client = zeep.Client(wsdl=config.WSDL)
    soap_loader = SoapLoader(client)
    news_saver = NewsSaver()
    news_parser = NewsParser()

    try:
        # load and parse comunio news
        soap_loader.load_news()
        news_parser.start()
        # load market values
        soap_loader.load_market_value_of_all_line_ups()
        print_summary()
    except ConnectionError:
        print("Connection Error")
    except Exception as e:
        print(e)
