from comalyzer import NewsParser
import unittest


class TestNewsParser(unittest.TestCase):
    seller_and_rest = 'von <a href="playerInfo.phtml?pid=11709610" target="_blank" style="font-weight:normal;" onclick="return(openSmallWindow(\'playerInfo.phtml?pid=11709610\',\'p_11709610\'))">Florian</a> zu Computer.<br />'

    def setUp(self):
        self.news_parser = NewsParser()

    def test_extract_player_id(self):
        self.news_parser.extract_player_id("123")
        self.assertEqual(self.news_parser.player_id, "123")

    def test_extract_player_name(self):
        self.news_parser.extract_player_name("</aJohn Doe")
        self.assertEqual(self.news_parser.player_name, "John Doe")

    def test_extract_price(self):
        self.news_parser.extract_price("160.000")
        self.assertEqual(self.news_parser.price, 160000)

    def test_extract_selling_manager_name(self):
        self.news_parser.extract_selling_manager(self.seller_and_rest)
        self.assertEqual(self.news_parser.seller, "Florian")

    def test_extract_selling_manager_id(self):
        self.news_parser.extract_selling_manager_id(self.seller_and_rest)
        self.assertEqual(self.news_parser.seller_id, "11709610")

    def test_is_computer_in_string(self):
        computer_string = "1234Computer"
        computer_wrong_place_string = "Computer"
        no_computer_string = "1234"
        self.assertTrue(self.news_parser.is_computer_in_string(computer_string))
        self.assertFalse(self.news_parser.is_computer_in_string(computer_wrong_place_string))
        self.assertFalse(self.news_parser.is_computer_in_string(no_computer_string))
