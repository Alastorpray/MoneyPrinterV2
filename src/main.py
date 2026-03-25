import os
import sys
import schedule
import subprocess

from art import *
from cache import *
from utils import *
from config import *
from status import *
from uuid import uuid4
from constants import *
from classes.Tts import TTS
from termcolor import colored
from classes.Twitter import Twitter
from classes.YouTube import YouTube
from prettytable import PrettyTable
from classes.Outreach import Outreach
from classes.AFM import AffiliateMarketing
from llm_provider import list_models, select_model, get_active_model


def show_menu(title, options):
    """Displays a numbered menu and returns the validated integer choice."""
    while True:
        info(f"\n============ {title} ============", False)
        for idx, option in enumerate(options):
            print(colored(f" {idx + 1}. {option}", "cyan"))
        info("=" * (len(title) + 26) + "\n", False)

        raw = input("Select an option: ").strip()
        if raw == '':
            print("\n" * 100)
            print("Invalid input: Empty input is not allowed.")
            continue
        try:
            return int(raw)
        except ValueError:
            print("\n" * 100)
            print(f"Invalid input: could not convert '{raw}' to a number.")


def select_account(provider, cached_accounts, display_fields):
    """Displays accounts table and handles selection or deletion.

    Returns the selected account dict, or None if the user deleted an account
    or made an invalid selection.
    """
    table = PrettyTable()
    table.field_names = ["ID"] + [f.title() for f in display_fields]

    for idx, account in enumerate(cached_accounts):
        row = [idx + 1]
        for field in display_fields:
            row.append(colored(account[field], "cyan"))
        table.add_row(row)

    print(table)
    info("Type 'd' to delete an account.", False)

    user_input = question("Select an account to start (or 'd' to delete): ").strip()

    if user_input.lower() == "d":
        delete_input = question("Enter account number to delete: ").strip()
        try:
            idx = int(delete_input) - 1
            if 0 <= idx < len(cached_accounts):
                account_to_delete = cached_accounts[idx]
                confirm = question(
                    f"Are you sure you want to delete '{account_to_delete['nickname']}'? (Yes/No): "
                ).strip().lower()
                if confirm == "yes":
                    remove_account(provider, account_to_delete["id"])
                    success("Account removed successfully!")
                else:
                    warning("Account deletion canceled.", False)
            else:
                error("Invalid account selected. Please try again.", "red")
        except ValueError:
            error("Invalid input. Please enter a number.", "red")
        return None

    try:
        idx = int(user_input) - 1
        if 0 <= idx < len(cached_accounts):
            return cached_accounts[idx]
    except ValueError:
        pass

    error("Invalid account selected. Please try again.", "red")
    return None


def create_account_youtube():
    """Prompts the user to create a new YouTube account."""
    generated_uuid = str(uuid4())
    success(f" => Generated ID: {generated_uuid}")
    nickname = question(" => Enter a nickname for this account: ")
    fp_profile = question(" => Enter the path to the Firefox profile: ")
    niche = question(" => Enter the account niche: ")
    language = question(" => Enter the account language: ")

    add_account("youtube", {
        "id": generated_uuid,
        "nickname": nickname,
        "firefox_profile": fp_profile,
        "niche": niche,
        "language": language,
        "videos": [],
    })
    success("Account configured successfully!")


def create_account_twitter():
    """Prompts the user to create a new Twitter account."""
    generated_uuid = str(uuid4())
    success(f" => Generated ID: {generated_uuid}")
    nickname = question(" => Enter a nickname for this account: ")
    fp_profile = question(" => Enter the path to the Firefox profile: ")
    topic = question(" => Enter the account topic: ")

    add_account("twitter", {
        "id": generated_uuid,
        "nickname": nickname,
        "firefox_profile": fp_profile,
        "topic": topic,
        "posts": [],
    })


def setup_cron_job(platform, account_id, cron_options):
    """Sets up a scheduled job for a platform."""
    info("How often do you want to run?")
    user_input = show_menu("SCHEDULE", cron_options)

    cron_script_path = os.path.join(ROOT_DIR, "src", "cron.py")
    command = ["python", cron_script_path, platform, account_id, get_active_model()]

    def job():
        subprocess.run(command)

    if user_input == 1:
        schedule.every(1).day.do(job)
        success("Set up CRON Job.")
    elif user_input == 2:
        schedule.every().day.at("10:00").do(job)
        schedule.every().day.at("16:00").do(job)
        success("Set up CRON Job.")
    elif user_input == 3 and len(cron_options) > 3:
        schedule.every().day.at("08:00").do(job)
        schedule.every().day.at("12:00").do(job)
        schedule.every().day.at("18:00").do(job)
        success("Set up CRON Job.")
    else:
        return False  # signal to go back
    return True


def handle_youtube():
    """Handles the YouTube Shorts Automater flow."""
    info("Starting YT Shorts Automater...")
    cached_accounts = get_accounts("youtube")

    if len(cached_accounts) == 0:
        warning("No accounts found in cache. Create one now?")
        if question("Yes/No: ").lower() == "yes":
            create_account_youtube()
        return

    selected = select_account("youtube", cached_accounts, ["id", "nickname", "niche"])
    if selected is None:
        return

    youtube = YouTube(
        selected["id"],
        selected["nickname"],
        selected["firefox_profile"],
        selected["niche"],
        selected["language"],
    )

    while True:
        rem_temp_files()
        user_input = show_menu("YOUTUBE", YOUTUBE_OPTIONS)
        tts = TTS()

        if user_input == 1:
            youtube.generate_video(tts)
            if question("Do you want to upload this video to YouTube? (Yes/No): ").lower() == "yes":
                youtube.upload_video()
        elif user_input == 2:
            videos = youtube.get_videos()
            if len(videos) > 0:
                videos_table = PrettyTable()
                videos_table.field_names = ["ID", "Date", "Title"]
                for idx, video in enumerate(videos):
                    videos_table.add_row([
                        idx + 1,
                        colored(video["date"], "blue"),
                        colored(video["title"][:60] + "...", "green"),
                    ])
                print(videos_table)
            else:
                warning(" No videos found.")
        elif user_input == 3:
            setup_cron_job("youtube", selected["id"], YOUTUBE_CRON_OPTIONS)
        elif user_input == 4:
            if get_verbose():
                info(" => Climbing Options Ladder...", False)
            break


def handle_twitter():
    """Handles the Twitter Bot flow."""
    info("Starting Twitter Bot...")
    cached_accounts = get_accounts("twitter")

    if len(cached_accounts) == 0:
        warning("No accounts found in cache. Create one now?")
        if question("Yes/No: ").lower() == "yes":
            create_account_twitter()
        return

    selected = select_account("twitter", cached_accounts, ["id", "nickname", "topic"])
    if selected is None:
        return

    twitter = Twitter(
        selected["id"],
        selected["nickname"],
        selected["firefox_profile"],
        selected["topic"],
    )

    while True:
        user_input = show_menu("TWITTER", TWITTER_OPTIONS)

        if user_input == 1:
            twitter.post()
        elif user_input == 2:
            posts = twitter.get_posts()
            posts_table = PrettyTable()
            posts_table.field_names = ["ID", "Date", "Content"]
            for idx, post in enumerate(posts):
                posts_table.add_row([
                    idx + 1,
                    colored(post["date"], "blue"),
                    colored(post["content"][:60] + "...", "green"),
                ])
            print(posts_table)
        elif user_input == 3:
            setup_cron_job("twitter", selected["id"], TWITTER_CRON_OPTIONS)
        elif user_input == 4:
            if get_verbose():
                info(" => Climbing Options Ladder...", False)
            break


def handle_affiliate_marketing():
    """Handles the Affiliate Marketing flow."""
    info("Starting Affiliate Marketing...")
    cached_products = get_products()

    if len(cached_products) == 0:
        warning("No products found in cache. Create one now?")
        if question("Yes/No: ").lower() != "yes":
            return

        affiliate_link = question(" => Enter the affiliate link: ")
        twitter_uuid = question(" => Enter the Twitter Account UUID: ")

        account = None
        for acc in get_accounts("twitter"):
            if acc["id"] == twitter_uuid:
                account = acc
                break

        if account is None:
            error("Twitter account not found with that UUID.")
            return

        add_product({
            "id": str(uuid4()),
            "affiliate_link": affiliate_link,
            "twitter_uuid": twitter_uuid,
        })

        afm = AffiliateMarketing(
            affiliate_link, account["firefox_profile"],
            account["id"], account["nickname"], account["topic"],
        )
        afm.generate_pitch()
        afm.share_pitch("twitter")
        return

    table = PrettyTable()
    table.field_names = ["ID", "Affiliate Link", "Twitter Account UUID"]
    for idx, product in enumerate(cached_products):
        table.add_row([
            idx + 1,
            colored(product["affiliate_link"], "cyan"),
            colored(product["twitter_uuid"], "blue"),
        ])
    print(table)

    raw = question("Select a product to start: ").strip()
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(cached_products):
            selected_product = cached_products[idx]
        else:
            error("Invalid product selected. Please try again.", "red")
            return
    except ValueError:
        error("Invalid input. Please enter a number.", "red")
        return

    account = None
    for acc in get_accounts("twitter"):
        if acc["id"] == selected_product["twitter_uuid"]:
            account = acc
            break

    if account is None:
        error("Linked Twitter account not found.")
        return

    afm = AffiliateMarketing(
        selected_product["affiliate_link"], account["firefox_profile"],
        account["id"], account["nickname"], account["topic"],
    )
    afm.generate_pitch()
    afm.share_pitch("twitter")


def handle_outreach():
    """Handles the Outreach flow."""
    info("Starting Outreach...")
    outreach = Outreach()
    outreach.start()


def main():
    """Main menu loop."""
    user_input = show_menu("OPTIONS", OPTIONS)

    if user_input == 1:
        handle_youtube()
    elif user_input == 2:
        handle_twitter()
    elif user_input == 3:
        handle_affiliate_marketing()
    elif user_input == 4:
        handle_outreach()
    elif user_input == 5:
        if get_verbose():
            print(colored(" => Quitting...", "blue"))
        sys.exit(0)
    else:
        error("Invalid option selected. Please try again.", "red")


if __name__ == "__main__":
    print_banner()

    first_time = get_first_time_running()
    if first_time:
        print(colored(
            "Hey! It looks like you're running MoneyPrinter V2 for the first time. Let's get you setup first!",
            "yellow",
        ))

    assert_folder_structure()
    rem_temp_files()
    fetch_songs()

    configured_model = get_ollama_model()
    if configured_model:
        select_model(configured_model)
        success(f"Using configured model: {configured_model}")
    else:
        try:
            models = list_models()
        except Exception as e:
            error(f"Could not connect to Ollama: {e}")
            sys.exit(1)

        if not models:
            error("No models found on Ollama. Pull a model first (e.g. 'ollama pull llama3.2:3b').")
            sys.exit(1)

        info("\n========== OLLAMA MODELS =========", False)
        for idx, model_name in enumerate(models):
            print(colored(f" {idx + 1}. {model_name}", "cyan"))
        info("==================================\n", False)

        model_choice = None
        while model_choice is None:
            raw = input(colored("Select a model: ", "magenta")).strip()
            try:
                choice_idx = int(raw) - 1
                if 0 <= choice_idx < len(models):
                    model_choice = models[choice_idx]
                else:
                    warning("Invalid selection. Try again.")
            except ValueError:
                warning("Please enter a number.")

        select_model(model_choice)
        success(f"Using model: {model_choice}")

    while True:
        main()
