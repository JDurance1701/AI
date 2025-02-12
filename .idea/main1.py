import requests
from fastapi import FastAPI
import fastapi
from pydantic import BaseModel
import uvicorn
import os
import signal
import logging
import math
import random
#import pytest

"""
By Todd Dole, Revision 1.2
Written for Hardin-Simmons CSCI-4332 Artificial Intelligence
Revision History
1.0 - API setup
1.1 - Very basic test player
1.2 - Bugs fixed and player improved, should no longer forfeit
"""

# TODO - Change the PORT and USER_NAME Values before running
DEBUG = True
PORT = 10300
USER_NAME = "jd2112b"
# TODO - change your method of saving information from the very rudimentary method here
hand = [] # list of Card objects in our hand
discard = [] # list of Card objects organized as a stack
cannot_discard = ""
oppknown = []
player_melds = []
stock = [] # list of Card objects in the stock pile
rank_order = {
    "A": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "T": 10,
    "J": 11,
    "Q": 12,
    "K": 13
}
placedMelds = []
oppplacedMelds = []
# set up the FastAPI application
app = FastAPI()

# set up the API endpoints
@app.get("/")
async def root():
    ''' Root API simply confirms API is up and running.'''
    return {"status": "Running"}

# data class used to receive data from API POST
class GameInfo(BaseModel):
    game_id: str
    opponent: str
    hand: str





@app.post("/start-2p-game/")
async def start_game(game_info: GameInfo):
    print("Logging test: Reached start_game function")
    logging.info("Logging test: Reached start_game function")
    ''' Game Server calls this endpoint to inform player a new game is starting. '''
    # TODO - Your code here - replace the lines below
    global hand
    global discard
    global meld

    #Store the hand in the global variable hand as Card objects and sort it
    card_strings = game_info.hand.split(" ")
    hand = [Card(card[:-1], card[-1]) for card in card_strings] #
    hand.sort()


    #Loop to print the hand separated by commas, no new line
    print("2p game started, hand is ", end="")
    print_hand()

    logging.info("2p game started, hand is "+str(hand))
    return {"status": "OK"}

# data class used to receive data from API POST
class HandInfo(BaseModel):
    hand: str

@app.post("/start-2p-hand/")
async def start_hand(hand_info: HandInfo):

    ''' Game Server calls this endpoint to inform player a new hand is starting, continuing the previous game. '''
    # TODO - Your code here
    global hand
    global discard
    global meld
    discard = []
    #Store the hand in the global variable hand as Card objects and sort it
    card_strings = hand_info.hand.split(" ")
    hand = [Card(card[:-1], card[-1]) for card in card_strings]            #
    hand.sort()

    print("2p hand started, hand is ", end="")
    print_hand()

    logging.info("2p hand started, hand is " + str(hand))
    return {"status": "OK"}

def print_hand():
    ''' Prints the hand in a readable format '''
    global hand
    for card in hand:
        print(card, end=", ")
    print()

def process_events(event_text):
    global hand
    global discard
    for event_line in event_text.splitlines():
        if ((USER_NAME + " draws") in event_line or (USER_NAME + " takes") in event_line):
            card_str = event_line.split(" ")[-1]  # Get card string
            rank = card_str[:-1]
            suit = card_str[-1]
            card = Card(rank, suit)  # Create Card object
            hand.append(card)  # Add Card object to hand
            hand.sort()
            print(f"Drew a {card}, hand is now: ")  # Use f-string for logging
            print_hand()
            logging.info(f"Drew a {card}, hand is now: {hand}")  # Use f-string for logging

        if "discards" in event_line:
            card_str = event_line.split(" ")[-1]  # Get card string
            rank = card_str[:-1]
            suit = card_str[-1]
            card = Card(rank, suit)  # Create Card object
            discard.insert(0, card)  # Add Card object to discard

        if "takes" in event_line:
            discard.pop(0)  # discard already contains Card objects

        if " Ends:" in event_line:
            print(event_line)

# data class used to receive data from API POST
class UpdateInfo(BaseModel):
    game_id: str
    event: str


@app.post("/update-2p-game/")
async def update_2p_game(update_info: UpdateInfo):
    '''
        Game Server calls this endpoint to update player on game status and other players' moves.
        Typically only called at the end of game.
    '''
    # TODO - Your code here - update this section if you want
    process_events(update_info.event)
    print(update_info.event)
    return {"status": "OK"}

@app.post("/draw/")
async def draw(update_info: UpdateInfo):
    global cannot_discard
    process_events(update_info.event)

    if not discard:  # More Pythonic check for empty list
        cannot_discard = ""
        print("Discard pile is empty, drawing from stock")
        return {"play": "draw stock"}

    top_discard = discard[0]  # Card object at the top of the discard pile

    # 1. Check for an exact match:
    if any(card.rank == top_discard.rank for card in hand):
        cannot_discard = top_discard
        print("Drawing from discard pile")
        return {"play": "draw discard"}

    # 2. Check for +/- 1 rank (considering Ace as low):
    try:
        top_rank_int = int(top_discard.rank)
    except ValueError:  # Handle T, J, Q, K, A
        top_rank_int = rank_order.get(top_discard.rank) # use rank_order dict to get int value


    for card in hand:
        try:
            card_rank_int = int(card.rank)
        except ValueError:
            card_rank_int = rank_order.get(card.rank)
        if abs(card_rank_int - top_rank_int) == 1:
            cannot_discard = top_discard
            print("Drawing from discard pile")
            return {"play": "draw discard"}

    print("Drawing from stock pile")
    return {"play": "draw stock"}  # Otherwise, draw from stock

def get_of_a_kind_count(hand):
    of_a_kind_count = [0, 0, 0, 0]
    if not hand: # handle empty hand case
      return of_a_kind_count
    last_card = hand[0]
    count = 0
    for card in hand:
        if card.rank == last_card.rank:
            count += 1
        else:
            of_a_kind_count[count-1] += 1  # Adjust index (0-based)
            count = 1 # reset to 1 not 0
        last_card = card
    of_a_kind_count[count-1] += 1  # Process the last card
    return of_a_kind_count

def get_count(hand, card):
    return sum(1 for c in hand if c.rank == card.rank) #Iterates through the hand and counts the number of cards with the same rank as the given card

#def test_get_of_a_kind_count():
#    assert get_of_a_kind_count(["2S", "2H", "2D", "7C", "7D", "7S", "7H", "QC", "QD", "QH", "AH"]) == [1, 0, 2, 1]
@app.post("/lay-down/")
async def lay_down(update_info: UpdateInfo):
    global hand, discard, cannot_discard
    process_events(update_info.event)

    # 1. Identify valid sets and runs
    sets = []
    runs = get_runs(hand)

    rank_counts = {}
    for card in hand:
        rank_counts[card.rank] = rank_counts.get(card.rank, 0) + 1

    for rank, count in rank_counts.items():
        if count >= 3:
            sets.append([card for card in hand if card.rank == rank])

    # 2. Meld new sets/runs and store them
    new_melds = sets + runs
    for meld in new_melds:
        player_melds.append(meld)
        for card in meld:
            hand.remove(card)

    meld_commands = [f"meld {' '.join(str(card) for card in meld)}" for meld in new_melds]

    # Print melds
    for meld in new_melds:
        print("Melding:", ', '.join(str(card) for card in meld))
    # 3. Lay off cards on existing melds
    layoff_commands = []
    for meld_index, meld in enumerate(player_melds):
        # Check if meld is a set or a run
        is_set = all(card.rank == meld[0].rank for card in meld)
        is_run = not is_set  # If it's not a set, it's a run

        meld_ranks = {get_rank_value(card.rank) for card in meld}
        meld_suits = {card.suit for card in meld}

        for card in hand[:]:
            card_rank = get_rank_value(card.rank)

            if is_set:
                    # Only allow layoffs for sets if the rank matches exactly
                if card.rank == meld[0].rank:
                    layoff_commands.append(f"layoff meld({meld_index}) {card}")
                    hand.remove(card)
                    meld.append(card)

            elif is_run:
                # Only allow layoffs for runs based on sequence and suit
                if card.suit in meld_suits and (card_rank - 1 in meld_ranks or card_rank + 1 in meld_ranks):
                    layoff_commands.append(f"layoff meld({meld_index}) {card}")
                    hand.remove(card)
                    meld.append(card)
    # 4. Determine discard
    discard_string = ""
    cards_to_keep = {card for meld in player_melds for card in meld}

    if hand:
        for card in hand[:]:
            if get_count(hand, card) == 1 and card not in cards_to_keep and card != cannot_discard:
                discard_string = f"discard {card}"
                hand.remove(card)
                print("Discarding single card:", card)
                break

        if not discard_string:
            for card in sorted(hand, reverse=True):
                if card not in cards_to_keep and card != cannot_discard:
                    discard_string = f"discard {card}"
                    hand.remove(card)
                    print("Discarding highest card:", card)
                    break

    # 5. Construct the play command
    play_string = " ".join(meld_commands + layoff_commands + [discard_string]).strip()

    print("Playing:", play_string)
    print("Hand is now:", end=" ")
    print_hand()
    logging.info("Playing: " + play_string)

    return {"play": play_string}

def get_runs(hand):
    runs = []
    current_run = []
    hand.sort()  # Ensure hand is sorted for run detection
    for i, card in enumerate(hand):
        if not current_run:
            current_run.append(card)
        else:
            prev_card = current_run[-1]
            try:
              if card.suit == prev_card.suit and int(card.rank) == int(prev_card.rank) + 1:
                  current_run.append(card)
              else:
                  if len(current_run) >= 3:
                      runs.append(current_run[:]) # append a copy
                  current_run = [card]
            except ValueError:
              if card.suit == prev_card.suit and rank_order[card.rank] == rank_order[prev_card.rank] + 1:
                  current_run.append(card)
              else:
                  if len(current_run) >= 3:
                      runs.append(current_run[:]) # append a copy
                  current_run = [card]
    if len(current_run) >= 3:
        runs.append(current_run[:]) # append a copy
    return runs



def get_runs(hand):
    runs = []
    current_run = []
    hand.sort()  # Ensure hand is sorted for run detection
    for i, card in enumerate(hand):
        if not current_run:
            current_run.append(card)
        else:
            prev_card = current_run[-1]
            try:
              if card.suit == prev_card.suit and int(card.rank) == int(prev_card.rank) + 1:
                  current_run.append(card)
              else:
                  if len(current_run) >= 3:
                      runs.append(current_run[:]) # append a copy
                  current_run = [card]
            except ValueError:
              if card.suit == prev_card.suit and rank_order[card.rank] == rank_order[prev_card.rank] + 1:
                  current_run.append(card)
              else:
                  if len(current_run) >= 3:
                      runs.append(current_run[:]) # append a copy
                  current_run = [card]
    if len(current_run) >= 3:
        runs.append(current_run[:]) # append a copy
    return runs

def current_state():
    ''' Returns the current state of the game '''
    global hand
    global discard
    global cannot_discard
    global oppknown
    global stock

    return {
        "hand": hand,
        "discard": discard,
        "cannot_discard": cannot_discard,
        "oppknown": oppknown,
        "stock": stock,
        "meld": meld
    }


class Card:
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit

    def __str__(self):  # For easy printing
        return f"{self.rank}{self.suit}"

    def __eq__(self, other): # For comparing cards, python calls this
        if isinstance(other, Card):
            return self.rank == other.rank and self.suit == other.suit
        return False

    def __lt__(self, other):
        if self.rank == other.rank:
            return self.suit < other.suit
        # Convert ranks to integer values using rank_order
        return rank_order[self.rank] < rank_order[other.rank]

    def __hash__(self):  # Add this method to make Card hashable
        return hash((self.rank, self.suit))


@app.get("/shutdown")
async def shutdown_API():
    ''' Game Server calls this endpoint to shut down the player's client after testing is completed.  Only used if DEBUG is True. '''
    os.kill(os.getpid(), signal.SIGTERM)
    logging.info("Player client shutting down...")
    return fastapi.Response(status_code=200, content='Server shutting down...')


''' Main code here - registers the player with the server via API call, and then launches the API to receive game information '''
if __name__ == "__main__":

    if (DEBUG):
        url = "http://127.0.0.1:16200/test"

        # TODO - Change logging.basicConfig if you want
        logging.basicConfig(filename="RummyPlayer.log", format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',level=logging.INFO)
    else:
        url = "http://127.0.0.1:16200/register"
        # TODO - Change logging.basicConfig if you want
        logging.basicConfig(filename="RummyPlayer.log", format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',level=logging.WARNING)

    payload = {
        "name": USER_NAME,
        "address": "127.0.0.1",
        "port": str(PORT)
    }

    try:
        # Call the URL to register client with the game server
        response = requests.post(url, json=payload)
    except Exception as e:
        print("Failed to connect to server.  Please contact Mr. Dole.")
        exit(1)

    if response.status_code == 200:
        print("Request succeeded.")
        print("Response:", response.json())  # or response.text
    else:
        print("Request failed with status:", response.status_code)
        print("Response:", response.text)
        exit(1)

    # run the client API using uvicorn
    uvicorn.run(app, host="127.0.0.1", port=PORT)
