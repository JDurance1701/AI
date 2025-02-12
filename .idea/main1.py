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


@app.post("/start-2p-hand/")  # Defines an endpoint that handles POST requests at "/start-2p-hand/"
async def start_hand(hand_info: HandInfo):  # Asynchronous function that takes a HandInfo object as input

    ''' Game Server calls this endpoint to inform player a new hand is starting, continuing the previous game. '''

    global hand  # Declares 'hand' as a global variable to store the player's hand
    global discard  # Declares 'discard' as a global variable to store discarded cards
    global meld  # Declares 'meld' as a global variable (though it's not used in this function)

    discard = []  # Resets the discard pile to an empty list at the start of a new hand

    # Extracts the card strings from the HandInfo object and splits them into individual card representations
    card_strings = hand_info.hand.split(" ")

    # Converts each card string into a Card object, where the rank is all but the last character
    # and the suit is the last character of the string
    hand = [Card(card[:-1], card[-1]) for card in card_strings]

    # Sorts the hand based on the card comparison rules defined in the Card class
    hand.sort()

    # Prints the new hand to the console, formatted nicely using print_hand()
    print("2p hand started, hand is ", end="")
    print_hand()

    # Logs the new hand information to the application's log system
    logging.info("2p hand started, hand is " + str(hand))

    # Returns a JSON response indicating success
    return {"status": "OK"}


def print_hand():
    ''' Prints the hand in a readable format '''
    global hand  # Accesses the global variable 'hand'
    for card in hand:  # Iterates through each card in the hand
        print(card, end=", ")  # Prints each card followed by a comma, staying on the same line
    print()  # Moves to the next line after printing all cards

def process_events(event_text):  # Processes a string of event logs and updates the game state accordingly
    global hand  # Declares 'hand' as a global variable to store the player's current hand
    global discard  # Declares 'discard' as a global variable to store discarded cards

    # Iterates through each line in the event text, which contains game events
    for event_line in event_text.splitlines():

        # Checks if the event line indicates that the user has drawn or taken a card
        if ((USER_NAME + " draws") in event_line or (USER_NAME + " takes") in event_line):
            card_str = event_line.split(" ")[-1]  # Extracts the card string from the event line
            rank = card_str[:-1]  # Gets the rank of the card (everything except the last character)
            suit = card_str[-1]  # Gets the suit of the card (last character)
            card = Card(rank, suit)  # Creates a Card object using the extracted rank and suit
            hand.append(card)  # Adds the new Card object to the player's hand
            hand.sort()  # Sorts the hand after adding the new card

            # Logs and prints the updated hand state
            print(f"Drew a {card}, hand is now: ")  # Displays the drawn card and updated hand
            print_hand()  # Calls the function to print the hand in a readable format
            logging.info(f"Drew a {card}, hand is now: {hand}")  # Logs the event

        # Checks if the event line indicates that a card was discarded
        if "discards" in event_line:
            card_str = event_line.split(" ")[-1]  # Extracts the discarded card string
            rank = card_str[:-1]  # Gets the rank of the discarded card
            suit = card_str[-1]  # Gets the suit of the discarded card
            card = Card(rank, suit)  # Creates a Card object
            discard.insert(0, card)  # Inserts the discarded card at the front of the discard pile

        # Checks if the event line indicates that a player took a card from the discard pile
        if "takes" in event_line:
            discard.pop(0)  # Removes the top card from the discard pile since it has been taken

        # Checks if the event line marks the end of a phase or round
        if " Ends:" in event_line:
            print(event_line)  # Prints the event line to indicate the phase or round has ended

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

@app.post("/draw/")  # Defines an endpoint for handling draw requests from the game server
async def draw(update_info: UpdateInfo):
    global cannot_discard  # Declares 'cannot_discard' as a global variable to track cards that cannot be discarded

    process_events(update_info.event)  # Processes any game events before making a drawing decision

    # Check if the discard pile is empty
    if not discard:  # More Pythonic way to check if a list is empty
        cannot_discard = ""  # Reset 'cannot_discard' since no discard exists
        print("Discard pile is empty, drawing from stock")  # Log the action
        return {"play": "draw stock"}  # Instruct the game to draw from the stockpile

    top_discard = discard[0]  # Retrieve the top card from the discard pile (a Card object)

    # 1. Check for an exact rank match with a card in hand
    if any(card.rank == top_discard.rank for card in hand):  # Look for a card in hand with the same rank
        cannot_discard = top_discard  # Mark this card as 'cannot_discard' to avoid discarding it immediately
        print("Drawing from discard pile")  # Log the action
        return {"play": "draw discard"}  # Instruct the game to draw from the discard pile

    # 2. Check if there is a card in hand with a rank that is +1 or -1 from the top discard card (for sequences)
    try:
        top_rank_int = int(top_discard.rank)  # Convert the rank of the top discard card to an integer (if numeric)
    except ValueError:  # If rank is not numeric (T, J, Q, K, A), retrieve its integer equivalent
        top_rank_int = rank_order.get(top_discard.rank)  # Use 'rank_order' dictionary to get the numeric value

    # Iterate through the player's hand to check for an adjacent rank match
    for card in hand:
        try:
            card_rank_int = int(card.rank)  # Convert the card rank to an integer if possible
        except ValueError:
            card_rank_int = rank_order.get(card.rank)  # Use dictionary lookup if the rank is a face card

        # Check if the rank difference is exactly 1
        if abs(card_rank_int - top_rank_int) == 1:
            cannot_discard = top_discard  # Mark this card as 'cannot_discard'
            print("Drawing from discard pile")  # Log the action
            return {"play": "draw discard"}  # Instruct the game to draw from the discard pile

    # If no suitable match is found, draw from the stockpile
    print("Drawing from stock pile")  # Log the action
    return {"play": "draw stock"}  # Default action is to draw from the stockpile

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
@app.post("/lay-down/")  # Defines an endpoint for handling the "lay down" action in the game
async def lay_down(update_info: UpdateInfo):
    global hand, discard, cannot_discard  # Declare global variables that will be modified
    process_events(update_info.event)  # Process any incoming game events before proceeding

    # 1. Identify valid sets and runs
    sets = []  # List to store sets (three or more of the same rank)
    runs = get_runs(hand)  # Find sequences (runs) in the hand

    rank_counts = {}  # Dictionary to count occurrences of each rank in the hand
    for card in hand:
        rank_counts[card.rank] = rank_counts.get(card.rank, 0) + 1  # Count each card rank

    # Identify sets (three or more cards of the same rank)
    for rank, count in rank_counts.items():
        if count >= 3:  # A set must have at least three cards of the same rank
            sets.append([card for card in hand if card.rank == rank])  # Collect matching cards into a set

    # 2. Meld new sets/runs and store them
    new_melds = sets + runs  # Combine all identified sets and runs

    for meld in new_melds:
        player_melds.append(meld)  # Store the new meld
        for card in meld:
            hand.remove(card)  # Remove the melded cards from the hand

    # Generate commands to send to the server for melding
    meld_commands = [f"meld {' '.join(str(card) for card in meld)}" for meld in new_melds]

    # Print melds for debugging
    for meld in new_melds:
        print("Melding:", ', '.join(str(card) for card in meld))

    # 3. Lay off cards on existing melds
    layoff_commands = []  # Store layoff commands

    for meld_index, meld in enumerate(player_melds):
        # Determine whether the meld is a set or a run
        is_set = all(card.rank == meld[0].rank for card in meld)  # True if all cards in meld have the same rank
        is_run = not is_set  # If it's not a set, it must be a run

        meld_ranks = {get_rank_value(card.rank) for card in meld}  # Store ranks of cards in the meld
        meld_suits = {card.suit for card in meld}  # Store suits of cards in the meld

        # Check if any card in the hand can be laid off onto an existing meld
        for card in hand[:]:  # Iterate over a copy of hand to allow safe removal
            card_rank = get_rank_value(card.rank)  # Get numerical rank value

            if is_set:
                # A set requires an exact rank match
                if card.rank == meld[0].rank:
                    layoff_commands.append(f"layoff meld({meld_index}) {card}")
                    hand.remove(card)  # Remove card from hand after laying off
                    meld.append(card)  # Add it to the existing meld

            elif is_run:
                # A run requires a sequence match in the same suit
                if card.suit in meld_suits and (card_rank - 1 in meld_ranks or card_rank + 1 in meld_ranks):
                    layoff_commands.append(f"layoff meld({meld_index}) {card}")
                    hand.remove(card)  # Remove card from hand after laying off
                    meld.append(card)  # Add it to the existing meld

    # 4. Determine discard
    discard_string = ""  # Initialize discard command
    cards_to_keep = {card for meld in player_melds for card in meld}  # Cards that should not be discarded

    if hand:  # Only proceed if there are still cards left in hand
        # Try to discard a single ungrouped card first
        for card in hand[:]:
            if get_count(hand, card) == 1 and card not in cards_to_keep and card != cannot_discard:
                discard_string = f"discard {card}"
                hand.remove(card)  # Remove discarded card from hand
                print("Discarding single card:", card)
                break

        # If no single ungrouped card was found, discard the highest card instead
        if not discard_string:
            for card in sorted(hand, reverse=True):  # Sort hand in descending order to discard highest-ranked card
                if card not in cards_to_keep and card != cannot_discard:
                    discard_string = f"discard {card}"
                    hand.remove(card)  # Remove discarded card from hand
                    print("Discarding highest card:", card)
                    break

    # 5. Construct the play command
    play_string = " ".join(meld_commands + layoff_commands + [discard_string]).strip()  # Combine all actions

    print("Playing:", play_string)  # Log the play command
    print("Hand is now:", end=" ")
    print_hand()  # Print remaining hand for debugging
    logging.info("Playing: " + play_string)  # Log the play action

    return {"play": play_string}  # Return play command to the server

# Helper function to find runs (sequential cards of the same suit)
def get_runs(hand):
    runs = []  # Store found runs
    current_run = []  # Temporary list to track a run in progress

    hand.sort()  # Sort hand so runs can be identified more easily

    for i, card in enumerate(hand):
        if not current_run:
            current_run.append(card)  # Start a new run with the current card
        else:
            prev_card = current_run[-1]  # Get the last card added to the current run
            try:
                # If card has the same suit and is one rank higher than the previous card, it's part of the run
                if card.suit == prev_card.suit and int(card.rank) == int(prev_card.rank) + 1:
                    current_run.append(card)
                else:
                    # If the current run is valid (3+ cards), store it before resetting
                    if len(current_run) >= 3:
                        runs.append(current_run[:])  # Append a copy of the run
                    current_run = [card]  # Start a new run
            except ValueError:  # Handle face cards (T, J, Q, K, A)
                if card.suit == prev_card.suit and rank_order[card.rank] == rank_order[prev_card.rank] + 1:
                    current_run.append(card)
                else:
                    if len(current_run) >= 3:
                        runs.append(current_run[:])  # Append a copy of the run
                    current_run = [card]  # Start a new run

    # If the last run found is valid, store it
    if len(current_run) >= 3:
        runs.append(current_run[:])  # Append a copy of the run

    return runs  # Return all detected runs


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