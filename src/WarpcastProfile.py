from random import choice, randint, uniform, sample, shuffle
from sys import stderr
from time import sleep
import json

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, NoSuchWindowException
from loguru import logger

from data.config import config
from src.AdspowerProfile import AdspowerProfile
from src.helpers import remove_line


class WarpcastProfile(AdspowerProfile):
    def __get_visible_elements(self, elements: list[WebElement]):
        visible_elements = []

        # need to adjust user visibility by navbar overlap
        nav_bar = self.driver.find_element(By.XPATH, '//nav[contains(@class, "sticky") and contains(@class, '
                                                     '"flex-col")]')
        nav_bar_height = nav_bar.size.get('height')

        win_upper_bound = self.driver.execute_script('return window.pageYOffset') + nav_bar_height
        win_height = self.driver.execute_script('return document.documentElement.clientHeight') - nav_bar_height
        win_lower_bound = win_upper_bound + win_height

        for element in elements:
            element_top_bound = element.location.get('y')
            element_height = element.size.get('height')
            element_lower_bound = element_top_bound + element_height

            if win_upper_bound <= element_top_bound and win_lower_bound >= element_lower_bound:
                visible_elements.append(element)

        return visible_elements

    def __use_search_input(self, text: str, press_enter: bool = True):
        logger.debug('__use_search_input: entered method')
        logger.debug('__use_search_input: selecting search input')
        search_input = self.wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="search"]')))
        self.human_hover(search_input, True)
        self.random_subactivity_sleep()

        logger.debug('__use_search_input: typing')
        self.human_type(text)
        self.random_subactivity_sleep()

        if press_enter:
            logger.debug('__use_search_input: pressing ENTER')
            self.action_chain.send_keys(Keys.ENTER).perform()
            self.random_subactivity_sleep()

    def __pick_cast_emoji(self):
        logger.debug('__pick_cast_emoji: entered method')
        self.random_subactivity_sleep()

        logger.debug('__pick_cast_emoji: pressing emoji button')
        select_emoji_button = self.driver.find_element(By.XPATH, '//div[@id="modal-root"]//div[@type="button"][2]')
        self.human_hover(select_emoji_button, click=True)
        self.random_subactivity_sleep()

        emoji_picker_shadow_root = self.driver.find_element(By.XPATH, '//em-emoji-picker').shadow_root

        logger.debug('__pick_cast_emoji: selecting emoji search input')
        emoji_search_input = emoji_picker_shadow_root.find_element(By.CSS_SELECTOR, 'input')
        self.human_hover(emoji_search_input, click=True)
        self.random_subactivity_sleep()

        logger.debug('__pick_cast_emoji: entering emoji name')
        with open('data/farm_data/emoji_names.txt', 'r', encoding="utf8") as file:
            all_emoji_names = [i.strip() for i in file]
        if not len(all_emoji_names):
            raise Exception('Missing emoji names, check data folder')

        emoji_name = choice(all_emoji_names)
        index_to = len(emoji_name) - 1 - randint(0, int(len(emoji_name) / 3)) \
            if len(emoji_name) > 4 else len(emoji_name)
        self.human_type(emoji_name[:index_to])
        self.random_subactivity_sleep()

        emoji_xpath_index = randint(0, config["max_deviation_from_search_result"])
        emoji_repeats = randint(1, config["max_emoji_repeat"])
        emojis_list = emoji_picker_shadow_root.find_elements(By.CSS_SELECTOR, 'div.category button')

        if len(emojis_list):
            try:
                emoji = emojis_list[emoji_xpath_index]
            except IndexError:
                emoji = emojis_list[0]

            for i in range(emoji_repeats):
                logger.debug('__pick_cast_emoji: selecting emoji')
                self.human_hover(emoji, click=True)
                self.random_subactivity_sleep()

        area_to_click_to_close_emoji_picker = self.driver.find_element(By.XPATH, '//div[@class="DraftEditor-root"]')
        self.human_hover(area_to_click_to_close_emoji_picker, click=True)
        self.random_subactivity_sleep()

    def __start_subscribing_with_scroll(self, min_scroll_episodes: int, max_scroll_episodes: int,
                                        min_subs_per_episode: int, max_subs_per_episode: int, buttons_xpath: str,
                                        dodge_popups: bool = False):
        logger.debug('__start_subscribing_with_scroll: entered method')
        for i in range(randint(min_scroll_episodes, max_scroll_episodes)):
            logger.debug('__start_subscribing_with_scroll: scrolling')
            self.human_scroll()
            self.random_subactivity_sleep()

            subscribe_buttons = self.driver.find_elements(By.XPATH, buttons_xpath)
            logger.debug(f'__start_subscribing_with_scroll: {len(subscribe_buttons)} subscribe_buttons')
            visible_subscribe_buttons = self.__get_visible_elements(subscribe_buttons)
            logger.debug(f'__start_subscribing_with_scroll: {len(visible_subscribe_buttons)} visible_subscribe_buttons')

            if len(visible_subscribe_buttons) == 0:
                logger.debug(f'__start_subscribing_with_scroll: no any visible subscribe buttons, continuing')
                self.random_subactivity_sleep()
                continue

            subscribes_per_episode = randint(min_subs_per_episode, max_subs_per_episode)
            if subscribes_per_episode > len(visible_subscribe_buttons):
                subscribes_per_episode = len(visible_subscribe_buttons)
            logger.debug(f'__start_subscribing_with_scroll: {subscribes_per_episode} subscribes_per_episode')

            shuffle(visible_subscribe_buttons)
            for subscribe in range(subscribes_per_episode):
                button_to_press = visible_subscribe_buttons.pop(0)
                logger.debug(f'__start_subscribing_with_scroll: going to subscribe')
                self.human_hover(button_to_press, True)
                logger.debug(f'__start_subscribing_with_scroll: subscribed')
                self.random_subactivity_sleep()

                if dodge_popups:
                    self.__dodge_popup()

    def __start_subscribing_without_scroll(self, amount: int, keep_order: bool, buttons_xpath: str,
                                           dodge_popups: bool = False):
        logger.debug('__start_subscribing_without_scroll: entered method')
        subscribe_buttons = self.driver.find_elements(By.XPATH, buttons_xpath)
        logger.debug(f'__start_subscribing_without_scroll: {len(subscribe_buttons)} subscribe_buttons')
        visible_subscribe_buttons = self.__get_visible_elements(subscribe_buttons)
        logger.debug(f'__start_subscribing_without_scroll: {len(visible_subscribe_buttons)} visible_subscribe_buttons')
        if len(visible_subscribe_buttons) == 0:
            raise Exception('No any visible subscribe buttons')

        if len(visible_subscribe_buttons) < amount:
            amount = len(visible_subscribe_buttons)

        logger.debug(f'__start_subscribing_without_scroll: keep_order {keep_order}')
        if not keep_order:
            logger.debug('__start_subscribing_without_scroll: not keeping order')
            shuffle(visible_subscribe_buttons)

        for subscribe in range(amount):
            logger.debug(f'__start_subscribing_without_scroll: going to subscribe')
            button_to_press = visible_subscribe_buttons.pop(0)
            self.human_hover(button_to_press, True)
            logger.debug(f'__start_subscribing_without_scroll: subscribed')
            self.random_subactivity_sleep()

            if dodge_popups:
                self.__dodge_popup()

    def __dodge_popup(self):
        logger.debug('__dodge_popup: entered method')
        for i in range(randint(config['popup_dodge']['min_tries'], config['popup_dodge']['max_tries'])):
            try:
                self.driver.find_element(By.CSS_SELECTOR, '[data-radix-popper-content-wrapper]')
                logger.debug('__dodge_popup: popup located, trying to dodge')

                x_offset = randint(config['popup_dodge']['min_width_deviation_px'],
                                   config['popup_dodge']['max_width_deviation_px'])
                y_offset = randint(config['popup_dodge']['min_height_deviation_px'],
                                   config['popup_dodge']['max_height_deviation_px'])

                x_is_positive = randint(0, 1)
                y_is_positive = randint(0, 1)

                x = x_offset if x_is_positive else -x_offset
                y = y_offset if y_is_positive else -y_offset

                logger.debug(f'__dodge_popup: x{x} y{y}')

                self.action_chain.move_by_offset(x, y).perform()
                self.random_subactivity_sleep()
            except NoSuchElementException:
                logger.debug('__dodge_popup: popup is not visible')
                return

        logger.debug('__dodge_popup: failed to dodge popup')

    def __switch_to_tab(self, url_includes_text: str):
        logger.debug('__switch_to_tab: entered method')
        logger.debug(f'__switch_to_tab: looking for tab that includes "{url_includes_text}"')
        for tab in self.driver.window_handles:
            try:
                self.driver.switch_to.window(tab)
                if url_includes_text in self.driver.current_url:
                    logger.debug(f'__switch_to_tab: switched to window "{self.driver.current_url}"')
                    return
            except:
                pass

        raise Exception(f'Failed to find tab that includes {url_includes_text} in url')

    def __wait_for_new_tab(self, init_tabs):
        logger.debug('__wait_for_new_tab: entered method')
        for i in range(config["element_wait_sec"]):
            if list(set(self.driver.window_handles) - set(init_tabs)):
                logger.debug('__wait_for_new_tab: found new tab')
                return
            else:
                sleep(1)

        raise Exception('Failed to locate new tab or extension window')

    def __close_all_other_tabs(self):
        initial_tab = self.driver.current_window_handle
        tabs_to_close = self.driver.window_handles
        tabs_to_close.remove(initial_tab)

        for tab in tabs_to_close:
            self.driver.switch_to.window(tab)
            self.driver.close()

        self.driver.switch_to.window(initial_tab)

    def visit_warpcast(self):
        start_tab = self.driver.current_window_handle
        try:
            self.__switch_to_tab('warpcast.com')
        except:
            self.driver.switch_to.window(start_tab)
            self.driver.get('https://warpcast.com/')

        if config["close_all_other_tabs"]:
            self.__close_all_other_tabs()

    def cast_on_homepage(self):
        with open('data/farm_data/casts.txt', 'r', encoding="utf8") as file:
            casts_raw = [i.strip() for i in file]

        casts = {}
        for cast_raw in casts_raw:
            profile_name, cast_text = cast_raw.split('|')
            if profile_name not in casts:
                casts[profile_name] = []
            casts[profile_name].append(cast_text)

        try:
            casts_for_profile = casts[self.profile_name]
            if config['cast_on_homepage']['keep_order']:
                cast_text = casts_for_profile[0]
            else:
                cast_text = choice(casts_for_profile)

        except KeyError:
            raise Exception('No any casts provided')

        logger.debug('cast_on_homepage: pressing cast button')
        cast_button = self.driver.find_element(By.XPATH, '//main//button[text()="Cast"]')
        self.human_hover(cast_button, click=True)
        self.random_subactivity_sleep()

        logger.debug('cast_on_homepage: entering cast text')
        self.human_type(cast_text + ' ')
        self.random_subactivity_sleep()

        to_use_emoji = True if uniform(0, 1) < config["use_emoji_in_cast_probability"] else False
        if to_use_emoji:
            self.__pick_cast_emoji()

        logger.debug('cast_on_homepage: pressing final cast button')
        final_cast_button = self.driver.find_element(By.XPATH, '//div[@id="modal-root"]//button[@title="Cast"]')
        self.human_hover(final_cast_button, click=True)
        self.random_subactivity_sleep()
        remove_line('data/farm_data/casts.txt', f'{self.profile_name}|{cast_text}')

    def subscribe_to_users_via_explore(self):
        logger.debug('subscribe_to_users: entered method')
        current_url = self.driver.current_url
        if current_url != 'https://warpcast.com/~/explore/users':
            logger.debug('subscribe_to_users: navigating to users list page')
            find_users_button = self.driver.find_element(By.XPATH, '//a[@title="Find Users"]')
            self.human_hover(find_users_button, click=True)
            self.random_subactivity_sleep()

        self.__start_subscribing_with_scroll(
            config['subscribe_via_explore']['min_scroll_episodes'],
            config['subscribe_via_explore']['max_scroll_episodes'],
            config['subscribe_via_explore']['min_subscribes_per_episode'],
            config['subscribe_via_explore']['max_subscribes_per_episode'],
            '//main//div[@class=" fade-in"]//button[text()="Follow"]'
        )

    def subscribe_to_channels_via_explore(self):
        logger.debug('subscribe_to_channels: entered method')
        current_url = self.driver.current_url
        if current_url != 'https://warpcast.com/~/explore/channels':
            if current_url != 'https://warpcast.com/~/explore/users':
                logger.debug('subscribe_to_users: navigating to users list page')
                find_users_button = self.driver.find_element(By.XPATH, '//a[@title="Find Users"]')
                self.human_hover(find_users_button, click=True)
                self.random_subactivity_sleep()

            logger.debug('subscribe_to_users: navigating to channels list page')
            find_channels_button = self.driver.find_element(By.XPATH, '//a[@title="Channels for you to follow"]')
            self.human_hover(find_channels_button, click=True)
            self.random_subactivity_sleep()

        self.__start_subscribing_with_scroll(
            config['subscribe_via_explore']['min_scroll_episodes'],
            config['subscribe_via_explore']['max_scroll_episodes'],
            config['subscribe_via_explore']['min_subscribes_per_episode'],
            config['subscribe_via_explore']['max_subscribes_per_episode'],
            '//main//div[@class=" fade-in"]//button[text()="Follow"]'
        )

    def surf_feed(self):
        def like(interaction_button_div: WebElement):
            logger.debug('surf_feed:like: pressing like button')
            like_button = interaction_button_div.find_element(By.XPATH, './/div[1]/div[1]/div[3]')
            self.human_hover(like_button, click=True)

        def recast(interaction_button_div: WebElement):
            logger.debug('surf_feed:recast: pressing recast button')
            recast_button = interaction_button_div.find_element(By.XPATH, './/div[1]//div[2]')
            self.human_hover(recast_button, click=True)
            self.random_subactivity_sleep()

            logger.debug('surf_feed:recast: pressing final recast button')
            final_recast_button = self.driver.find_element(By.XPATH, '//span[contains(text(), "Recast")]')
            self.human_hover(final_recast_button, click=True)

        def bookmark(interaction_button_div: WebElement):
            logger.debug('surf_feed:bookmark: pressing bookmark button')
            bookmark_button = interaction_button_div.find_element(By.XPATH, './/div[1]/div[2]/div')
            self.human_hover(bookmark_button, click=True)

        current_url = self.driver.current_url
        if current_url != 'https://warpcast.com/':
            logger.debug('surf_feed: navigating to home page')
            home_button = self.driver.find_element(By.XPATH, '//a[@title="Home"]')
            self.human_hover(home_button, click=True)
            self.random_subactivity_sleep()

        for i in range(randint(config['surf_feed']['min_scroll_episodes'],
                               config['surf_feed']['max_scroll_episodes'])):
            self.human_scroll()
            self.random_subactivity_sleep()

            to_recast = True if (uniform(0, 1) < config['surf_feed']['recast_probability']) else False
            to_like = True if (uniform(0, 1) < config['surf_feed']['like_probability']) else False
            to_bookmark = True if (uniform(0, 1) < config['surf_feed']['bookmark_probability']) else False
            logger.debug(f'surf_feed: recast - {to_recast}, like - {to_like}, bookmark - {to_bookmark}')

            if not to_recast + to_like + to_bookmark:
                logger.debug(f'surf_feed: to_recast + to_like + to_bookmark = 0')
                continue

            all_cast_interactions = []
            if to_recast:
                all_cast_interactions.append(recast)
            if to_like:
                all_cast_interactions.append(like)
            if to_bookmark:
                all_cast_interactions.append(bookmark)
            shuffle(all_cast_interactions)

            all_interaction_button_divs = self.driver.find_elements(
                By.XPATH, '//main/div/div/div[2]//div[contains(@class, " items-start")]')
            logger.debug(f'surf_feed: {len(all_interaction_button_divs)} all_interaction_button_divs')
            visible_interaction_button_divs = self.__get_visible_elements(all_interaction_button_divs)
            logger.debug(f'surf_feed: {len(visible_interaction_button_divs)} visible_interaction_button_divs')
            if not visible_interaction_button_divs:
                logger.debug(f'surf_feed: no any visible interaction button divs, skipping actions')
                continue

            for interaction in all_cast_interactions:
                try:
                    interaction(choice(visible_interaction_button_divs))
                    self.random_subactivity_sleep()
                except Exception:
                    break

            self.random_subactivity_sleep()

    def subscribe_to_authors_via_search(self):
        logger.debug('subscribe_to_authors_via_search: entered method')
        with open("data/farm_data/search_authors.txt", "r") as _file:
            all_text_lines = [i.strip() for i in _file]

        if not len(all_text_lines):
            raise Exception('Missing search text, check data folder')

        text = choice(all_text_lines)
        self.__use_search_input(text)
        if config['subscribe_to_authors_via_search']['remove_text_from_base']:
            remove_line("data/farm_data/search_authors.txt", text)

        use_scrolling_probability = config['subscribe_to_authors_via_search']['use_scrolling_probability']
        use_scrolling = True if uniform(0, 1) < use_scrolling_probability else False

        if not use_scrolling:
            keep_order_probability = config['subscribe_to_authors_via_search']['keep_order_probability']
            keep_order = True if uniform(0, 1) < keep_order_probability else False
            amount = randint(config['subscribe_to_authors_via_search']['min_subscribes'],
                             config['subscribe_to_authors_via_search']['max_subscribes'])
            self.__start_subscribing_without_scroll(
                amount, keep_order, '//div[contains(@title, "Follow")]/*[local-name()="svg"]', True)
        else:
            self.__start_subscribing_with_scroll(
                config['subscribe_to_authors_via_search']['min_scroll_episodes'],
                config['subscribe_to_authors_via_search']['max_scroll_episodes'],
                config['subscribe_to_authors_via_search']['min_subscribes_per_episode'],
                config['subscribe_to_authors_via_search']['max_subscribes_per_episode'],
                '//div[contains(@title, "Follow")]/*[local-name()="svg"]',
                True
            )

    def subscribe_to_channels_via_search(self):
        logger.debug('subscribe_to_channels_via_search: entered method')
        with open("data/farm_data/search_channels.txt", "r") as _file:
            all_text_lines = [i.strip() for i in _file]

        if not len(all_text_lines):
            raise Exception('Missing search text, check data folder')

        text = choice(all_text_lines)
        self.__use_search_input(text)
        if config['subscribe_to_channels_via_search']['remove_text_from_base']:
            remove_line("data/farm_data/search_channels.txt", text)

        find_channels_button = self.driver.find_element(By.XPATH, '//a[@title="Channels found based on your search"]')
        self.human_hover(find_channels_button, click=True)
        self.random_subactivity_sleep()

        use_scrolling_probability = config['subscribe_to_channels_via_search']['use_scrolling_probability']
        use_scrolling = True if uniform(0, 1) < use_scrolling_probability else False

        if not use_scrolling:
            keep_order_probability = config['subscribe_to_channels_via_search']['keep_order_probability']
            keep_order = True if uniform(0, 1) < keep_order_probability else False
            amount = randint(config['subscribe_to_channels_via_search']['min_subscribes'],
                             config['subscribe_to_channels_via_search']['max_subscribes'])
            self.__start_subscribing_without_scroll(amount, keep_order,
                                                    '//main//div[@class=" fade-in"]//button[text()="Follow"]')
        else:
            self.__start_subscribing_with_scroll(
                config['subscribe_to_channels_via_search']['min_scroll_episodes'],
                config['subscribe_to_channels_via_search']['max_scroll_episodes'],
                config['subscribe_to_channels_via_search']['min_subscribes_per_episode'],
                config['subscribe_to_channels_via_search']['max_subscribes_per_episode'],
                '//main//div[@class=" fade-in"]//button[text()="Follow"]'
            )

    def subscribe_to_users_via_search(self):
        logger.debug('subscribe_to_users_via_search: entered method')
        with open("data/farm_data/search_users.txt", "r") as _file:
            all_text_lines = [i.strip() for i in _file]

        if not len(all_text_lines):
            raise Exception('Missing search text, check data folder')

        text = choice(all_text_lines)
        self.__use_search_input(text)
        if config['subscribe_to_users_via_search']['remove_text_from_base']:
            remove_line("data/farm_data/search_users.txt", text)

        find_users_button = self.driver.find_element(By.XPATH, '//a[@title="Users found based on your search"]')
        self.human_hover(find_users_button, click=True)
        self.random_subactivity_sleep()

        use_scrolling_probability = config['subscribe_to_users_via_search']['use_scrolling_probability']
        use_scrolling = True if uniform(0, 1) < use_scrolling_probability else False

        if not use_scrolling:
            keep_order_probability = config['subscribe_to_users_via_search']['keep_order_probability']
            keep_order = True if uniform(0, 1) < keep_order_probability else False
            amount = randint(config['subscribe_to_users_via_search']['min_subscribes'],
                             config['subscribe_to_users_via_search']['max_subscribes'])
            self.__start_subscribing_without_scroll(amount, keep_order,
                                                    '//main//div[@class=" fade-in"]//button[text()="Follow"]')
        else:
            self.__start_subscribing_with_scroll(
                config['subscribe_to_users_via_search']['min_scroll_episodes'],
                config['subscribe_to_users_via_search']['max_scroll_episodes'],
                config['subscribe_to_users_via_search']['min_subscribes_per_episode'],
                config['subscribe_to_users_via_search']['max_subscribes_per_episode'],
                '//main//div[@class=" fade-in"]//button[text()="Follow"]'
            )

    def subscribe_to_mandatory_users(self):
        self.__mandatory_subscribe(True)

    def subscribe_to_mandatory_channels(self):
        self.__mandatory_subscribe(False)

    def __mandatory_subscribe(self, to_users: bool):
        def direct_link_subscribe(target_name: str):
            url = f'https://warpcast.com/{target_name}' if to_users else f'https://warpcast.com/~/channel/{target_name}'
            self.driver.get(url)
            self.random_subactivity_sleep()

            subscribe_button = self.driver.find_element(By.XPATH, '//main//button[contains(text(),"ollow")]')
            if subscribe_button.text == "Follow":
                self.human_hover(subscribe_button, click=True)
            else:
                logger.info(f'{self.profile_name} - already subscribed to target {target_name}')

        def subscribe_via_search(target_name: str):
            self.__use_search_input(target_name, False)
            self.random_subactivity_sleep()

            options_list = self.driver.find_element(By.XPATH, f'//form//div[text()="Users"]/../div[2]')
            all_options = options_list.find_elements(By.XPATH, 'div')

            for option in all_options:
                username = option.find_element(By.CSS_SELECTOR, 'div[class = "text-muted text-sm"]').text
                if username.replace('@', '') == target_name:
                    logger.debug('__mandatory_subscribe:subscribe_via_search: found target, subscribing')
                    self.human_hover(option, True)
                    self.random_subactivity_sleep()

                    subscribe_button = self.driver.find_element(By.XPATH, '//main//button[contains(text(),"ollow")]')
                    if subscribe_button.text == "Follow":
                        self.human_hover(subscribe_button, click=True)
                    else:
                        logger.info(f'{self.profile_name} - already subscribed to target {target_name}')
                    return

            raise Exception()

        with open('data/profile_logs.json') as file:
            profile_logs = json.load(file)

        if to_users:
            logger.debug('__mandatory_subscribe: subscribing to users')
            subscribe_config = config['subscribe_to_mandatory_users']
            already_subscribed = profile_logs[self.profile_name]['mandatory_users_subscribes']
            with open('data/farm_data/subscribe_to_users.txt', 'r', encoding="utf8") as file:
                subscribe_targets = [i.strip() for i in file]
        else:
            logger.debug('__mandatory_subscribe: subscribing to channels')
            subscribe_config = config['subscribe_to_mandatory_channels']
            already_subscribed = profile_logs[self.profile_name]['mandatory_channels_subscribes']
            with open('data/farm_data/subscribe_to_channels.txt', 'r', encoding="utf8") as file:
                subscribe_targets = [i.strip() for i in file]

        remaining_subscribe_targets = list(set(subscribe_targets) - set(already_subscribed))
        shuffle(remaining_subscribe_targets)
        logger.debug(f'__mandatory_subscribe: {len(remaining_subscribe_targets)} remaining_subscribe_targets')
        if not remaining_subscribe_targets:
            logger.info(f'{self.profile_name} - already subscribed to all targets')
            return

        subscribes_count = randint(subscribe_config['min_subscribes_per_run'],
                                   subscribe_config['max_subscribes_per_run'])

        if subscribes_count > len(remaining_subscribe_targets):
            subscribes_count = len(remaining_subscribe_targets)
        logger.debug(f'__mandatory_subscribe: {subscribes_count} subscribes_count')

        for i in range(subscribes_count):
            target = remaining_subscribe_targets.pop(0)
            if to_users:
                use_direct_link = True if uniform(0, 1) < subscribe_config["use_direct_link_probability"] else False
            else:
                use_direct_link = True

            logger.debug(f'__mandatory_subscribe: {use_direct_link} use_direct_link')

            try:
                if use_direct_link:
                    direct_link_subscribe(target)
                else:
                    subscribe_via_search(target)

                logger.info(f'{self.profile_name} - subscribed to {target}')

                log_update_key = "mandatory_users_subscribes" if to_users else "mandatory_channels_subscribes"
                profile_logs[self.profile_name][log_update_key].append(target)
                with open("data/profile_logs.json", "w") as file:
                    json.dump(profile_logs, file, indent=4)

            except Exception:
                logger.error(f'{self.profile_name} - failed to subscribe to user, unexpected error')

            finally:
                self.random_activity_sleep()

    def connect_metamask(self):
        logger.debug('connect_metamask: entered method')

        def go_home():
            home_button = self.driver.find_element(By.XPATH, '//a[@href="/"]')
            self.human_hover(home_button, True)
            self.random_subactivity_sleep()

        def get_metamask_password() -> str:
            logger.debug('connect_metamask:get_metamask_password: entered method')
            with open('data/sensitive_data/metamask_passwords.txt', 'r') as file:
                metamask_passwords_raw = [i.strip() for i in file]

            _metamask_password = ''

            for line in metamask_passwords_raw:
                profile_name, password = line.split('|', 1)
                if profile_name == self.profile_name:
                    _metamask_password = password
                    break

            if not _metamask_password:
                raise Exception('Metamask password is not provided')

            return _metamask_password

        def process_wallet_connection():
            logger.debug('connect_metamask:process_wallet_connection: entered method')

            def unlock():
                logger.debug('connect_metamask:process_wallet_connection:unlock: entered method')
                pass_input = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//input[@data-testid="unlock-password"]')))
                pass_input.send_keys(metamask_password)
                unlock_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//button[@data-testid="unlock-submit"]')))
                unlock_button.click()
                logger.debug('connect_metamask:process_wallet_connection:unlock: unlocked wallet')

            def connect():
                try:  # if connection is cached there will not be connection request
                    logger.debug('connect_metamask:process_wallet_connection:connect: entered method')
                    next_button = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "btn-primary")]')))
                    next_button.click()
                    connect_button = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, '//button[@data-testid="page-container-footer-next"]')))
                    connect_button.click()
                    logger.debug('connect_metamask:process_wallet_connection:connect:  connected wallet')
                except NoSuchWindowException:  # cached connection
                    logger.debug('connect_metamask:process_wallet_connection:connect:  cached connection')
                    pass

            self.__switch_to_tab('chrome-extension')

            if '#unlock' in self.driver.current_url:
                logger.debug('connect_metamask:process_wallet_connection: need to unlock')
                unlock()
                logger.debug('connect_metamask:process_wallet_connection: connecting')
                connect()
            else:
                logger.debug('connect_metamask:process_wallet_connection: connecting')
                connect()

        def sign_with_metamask():
            logger.debug('connect_metamask:sign_with_metamask: entered method')

            def verify_origin(origin: str):
                logger.debug('connect_metamask:sign_with_metamask:verify_origin: entered method')
                current_origin = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, '//div[@class="signature-request__origin"]//span'))).text
                if current_origin != origin:
                    logger.debug("origin mismatch")
                    signature_cancel_button = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, '//button[@data-testid="signature-cancel-button"]')))
                    signature_cancel_button.click()
                    raise Exception(f'Origin mismatch, current: {current_origin}, required: {origin}')

            def sign():
                logger.debug('connect_metamask:sign_with_metamask:sign: entered method')
                verify_origin('https://verify.warpcast.com')

                try:
                    scroll_button = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, '//div[@data-testid="signature-request-scroll-button"]')))
                    scroll_button.click()
                except:
                    pass

                sign_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//button[@data-testid="signature-sign-button"]')))
                sign_button.click()

            self.__switch_to_tab('chrome-extension')
            sign()

        with open('data/profile_logs.json') as file:
            profile_logs = json.load(file)

        if profile_logs[self.profile_name]["wallet_connected"]:
            logger.info(f'{self.profile_name} - wallet is already connected')
            return

        metamask_password = get_metamask_password()

        logger.debug('connect_metamask: pressing profile button')
        profile_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//a[@title="Profile"]')))
        self.human_hover(profile_button, click=True)
        self.random_subactivity_sleep()

        profile_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//a[@title="Profile"]')))
        self.human_hover(profile_button, click=True)
        self.random_subactivity_sleep()

        try:  # to go home before Exception as here will be missing search and cast buttons
            edit_profile_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//button[text()="Edit Profile"]')))
            self.human_hover(edit_profile_button, click=True)
            self.random_subactivity_sleep()

            verified_addresses_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//a[@href="/~/settings/verified-addresses"]')))
            self.human_hover(verified_addresses_button, click=True)
            self.random_subactivity_sleep()
        except Exception as e:
            go_home()
            raise Exception(e)

        try:  # check if EVM wallet is already connected
            self.driver.find_element(By.XPATH, '//img[@src="/static/media/ethereumLogoPurple.a6ebba304034873ba05c.webp"]')
            logger.info(f'{self.profile_name} - looks like wallet was already connected before, skipping')

            profile_logs[self.profile_name]["wallet_connected"] = True
            with open("data/profile_logs.json", "w") as file:
                json.dump(profile_logs, file, indent=4)

            go_home()
            return
        except:
            pass

        try:  # to go home before Exception as here will be missing search and cast buttons
            verify_an_address_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//button[text()="Verify an address"]')))
            self.human_hover(verify_an_address_button, click=True)
            self.random_subactivity_sleep()
        except Exception as e:
            go_home()
            raise Exception(e)

        main_tab = self.driver.current_window_handle
        try:  # to go to main tab + go home before Exception as here will be missing search and cast buttons
            self.__switch_to_tab('verify.warpcast.com')
            warpcast_verify_tab = self.driver.current_window_handle
            self.random_subactivity_sleep()

            sleep(3)
            # if wallet is unlocked and connection is cached - there will not be connection button
            if self.driver.find_elements(By.XPATH, '//button[text()="Connect wallet"]'):
                connect_wallet_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//button[text()="Connect wallet"]')))
                self.human_hover(connect_wallet_button, click=True)
                self.random_subactivity_sleep()

                init_tabs = self.driver.window_handles
                metamask_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//button[@data-testid="rk-wallet-option-metaMask"]')))  # rk-wallet-option-io.metamask
                self.human_hover(metamask_button, click=True)
                self.random_subactivity_sleep()

                self.__wait_for_new_tab(init_tabs)
                process_wallet_connection()
                self.driver.switch_to.window(warpcast_verify_tab)
                self.random_subactivity_sleep()

            init_tabs = self.driver.window_handles
            sign_message_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//button[text()="Sign message"]')))
            self.human_hover(sign_message_button, click=True)
            self.random_subactivity_sleep()

            self.__wait_for_new_tab(init_tabs)
            sign_with_metamask()
            self.driver.switch_to.window(warpcast_verify_tab)
            self.random_subactivity_sleep()

            self.wait.until(EC.element_to_be_clickable((By.XPATH, '//button[text()="Return to Warpcast"]')))
            profile_logs[self.profile_name]["wallet_connected"] = True
            with open("data/profile_logs.json", "w") as file:
                json.dump(profile_logs, file, indent=4)

            self.driver.close()
            self.driver.switch_to.window(main_tab)
            go_home()

        except Exception as e:
            self.driver.switch_to.window(main_tab)
            self.random_subactivity_sleep()
            go_home()

            raise Exception(e)
