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

"""
By Todd Dole, Revision 1.1
Written for Hardin-Simmons CSCI-4332 Artificial Intelligence
Revision History
1.0 - API setup
1.1 - Very basic test player
"""

# TODO - Change the PORT and USER_NAME Values before running
DEBUG = True
PORT = 10300
USER_NAME = "jd2112b"
# TODO - change your method of saving information from the very rudimentary method here
hand = [] # list of cards in our hand
discard = [] # list of cards organized as a stack
gamehistory = [] # list of game history
stock = [] # list of cards in the stock pile
opponentknown = [] # list of cards in the opponent's hand that we know about
opponentprob = [] # list of cards in the opponent's hand that we think they have
melds = [] # list of melds we have made
oppmelds = [] # list of melds the opponent has made
depth_limit = 3 # depth limit for minimax
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
    "10": 10,
    "J": 11,
    "Q": 12,
    "K": 13
}
#Deck of 52 cards
deck = [str(i)+s for i in rank_order.keys() for s in ['C', 'D', 'H', 'S']]

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
    ''' Game Server calls this endpoint to inform player a new game is starting. '''
    # TODO - Your code here - replace the lines below
    global hand
    global discard
    hand = game_info.hand.split(" ")
    hand.sort()
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
    hand = hand_info.hand.split(" ").sort()
    logging.info("2p hand started, hand is " + str(hand))
    return {"status": "OK"}

def process_events(event_text):
    ''' Shared function to process event text from various API endpoints '''
    # TODO - Your code here. Everything from here to end of function
    global hand
    global discard
    for event_line in event_text.splitlines():

        if ((USER_NAME + " draws") in event_line or (USER_NAME + " takes") in event_line):
            print("In draw, hand is "+str(hand))
            hand.append(event_line.split(" ")[-1])
            hand.sort()
            print("Hand is now "+str(hand))
            logging.info("Drew a "+event_line.split(" ")[-1]+", hand is now: "+str(hand))
        if ("discards" in event_line):  # add a card to discard pile
            discard.insert(0, event_line.split(" ")[-1])
        if ("takes" in event_line): # remove a card from discard pile
            discard.pop(0)

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
    return {"status": "OK"}

@app.post("/draw/")
async def draw(update_info: UpdateInfo):
    ''' Game Server calls this endpoint to start player's turn with draw from discard pile or draw pile.'''
    # TODO - Your code here - everything from here to end of function
    process_events(update_info.event)
    if len(discard)<1: # If the discard pile is empty, draw from stock
        return {"play": "draw stock"}
    if any(discard[0][0] in s for s in hand): # if our hand contains a matching card, take it
        return {"play": "draw discard"}
    return {"play": "draw stock"} # Otherwise, draw from stock


@app.post("/lay-down/")
async def lay_down(update_info: UpdateInfo):
    global hand, discard
    process_events(update_info.event)

    current_state = get_current_state()  # Build the state for minimax

    # Use MCTS with Minimax for decision-making
    best_move = mcts_with_minimax(current_state, simulations=100)

    logging.info("Playing best move (MCTS+Minimax): " + str(best_move))
    return {"play": best_move}

def get_current_state():
    # Create a copy of the global game state variables
    return {
        'hand': hand.copy(),       # your current hand
        'discard': discard.copy(), # current discard pile
        'stock': stock.copy(),     # current stock pile
        'melds': melds.copy(),     # your current melds
        'oppmelds': oppmelds.copy(), # opponent's melds
        'gamehistory': gamehistory.copy(), # game history
        # Add any other state information you need (e.g., melds, opponent info)
    }


def generate_moves(state):
    """Generate all legal moves for the current state."""
    moves = []
    hand_copy = state['hand'][:]

    # Generate melds
    melds = generate_melds(state)

    # Remove melded cards from possible discard options
    discard_options = set(hand_copy)
    for meld in melds:
        for card in meld:
            discard_options.discard(card)

    # Add possible meld actions
    for meld in melds:
        moves.append({"action": "meld", "cards": meld})

    # Add discard actions
    for card in discard_options:
        moves.append({"action": "discard", "card": card})

    return moves

def generate_melds(state):
    """
    Generate all valid melds in hand:
    1. Three or more cards of the same rank.
    2. Three or more sequential cards of the same suit.
    """
    melds = []

    # Find sets (same rank)
    rank_dict = {}
    for card in state['hand']:
        rank, suit = card[:-1], card[-1]
        if rank not in rank_dict:
            rank_dict[rank] = []
        rank_dict[rank].append(card)

    for rank, cards in rank_dict.items():
        if len(cards) >= 3:
            melds.append(cards[:])  # Copy to avoid modifying original

    # Find runs (same suit, sequential rank)
    suits = {'C': [], 'D': [], 'H': [], 'S': []}
    for card in state['hand']:
        rank, suit = card[:-1], card[-1]
        suits[suit].append((int(rank_order[rank]), card))

    for suit, cards in suits.items():
        cards.sort()  # Sort by rank
        run = []
        for i in range(len(cards)):
            if not run or (cards[i][0] == run[-1][0] + 1):
                run.append(cards[i][1])
            else:
                if len(run) >= 3:
                    melds.append(run[:])  # Copy the run
                run = [cards[i][1]]
        if len(run) >= 3:
            melds.append(run)

    return melds





#Probably need to work on this later
def apply_move(state, move):
    """
    Apply a move to the state and return the new state.
    """
    new_state = state.copy()  # Copy state to avoid modifying original
    if move["action"] == "meld":
        for card in move["cards"]:
            if card in new_state['hand']:
                new_state['hand'].remove(card)
        new_state['melds'].append(move["cards"])

    elif move["action"] == "discard":
        if move["card"] in new_state['hand']:
            new_state['hand'].remove(move["card"])
            new_state['discard'].insert(0, move["card"])  # Add to discard pile

    return new_state

#Probably need to work on this later
def evaluate(state):
    """
    Evaluates the current game state.
    """
    score = 0

    # Reward completed melds
    for meld in state['melds']:
        score += len(meld) * 10  # More cards in meld = higher score

    # Penalize unmelded high-value cards
    for card in state['hand']:
        rank = card[:-1]
        score -= rank_order[rank]  # Higher cards = higher penalty

    return score


def game_over(state):
    """
    Determine if the game is over given the state.

    A game of Rummy ends if:
    1. A player has no cards left.
    2. (Optional) A player reaches a winning score.
    3. (Optional) The deck is empty, and no moves are possible.
    """
    # Check if any player has no cards left
    for player_hand in state["hands"]:
        if len(player_hand) == 0:
            return True  # The game ends when a player goes out.

    # Check if a score limit is reached (optional rule)
    if "scores" in state:
        max_score = max(state["scores"])
        if max_score >= state.get("winning_score", 100):  # Default winning score = 100
            return True

    # Check if the deck is empty and no moves are possible
    if len(state["deck"]) == 0 and not any_valid_moves(state):
        return True  # No more possible moves, game ends.

    return False  # The game continues

def any_valid_moves(state):
    """
    Checks if any player can make a valid move.
    """
    for player_hand in state["hands"]:
        if generate_moves({"hand": player_hand}):
            return True  # At least one valid move exists.
    return False  # No moves left.


def minimax(state, depth, alpha, beta, maximizing_player):
    if depth == 0 or game_over(state):
        return evaluate(state)

    if maximizing_player:
        max_eval = float('-inf')
        for move in generate_moves(state):
            new_state = apply_move(state, move)
            eval = minimax(new_state, depth - 1, alpha, beta, False)
            max_eval = max(max_eval, eval)
            alpha = max(alpha, eval)
            if beta <= alpha:
                break  # Alpha-beta pruning
        return max_eval
    else:
        min_eval = float('inf')
        for move in generate_moves(state):
            new_state = apply_move(state, move)
            eval = minimax(new_state, depth - 1, alpha, beta, True)
            min_eval = min(min_eval, eval)
            beta = min(beta, eval)
            if beta <= alpha:
                break  # Alpha-beta pruning
        return min_eval


#TreeNode
class TreeNode:
    def __init__(self, state, parent=None):
        self.state = state  # Current game state
        self.parent = parent
        self.children = []
        self.visits = 0
        self.value = 0  # Accumulated reward

    def is_fully_expanded(self):
        """Checks if all possible moves have been explored."""
        return len(self.children) == len(generate_moves(self.state))

    def best_child(self, exploration_weight=1.4):
        """Uses UCB1 formula to select the best child node."""
        return max(self.children, key=lambda c: (c.value / (c.visits + 1e-6)) +
                                                exploration_weight * math.sqrt(
            math.log(self.visits + 1) / (c.visits + 1e-6)))

def mcts_with_minimax(root_state, simulations=100):
    """Perform MCTS with Minimax rollout."""
    root = TreeNode(root_state)

    for _ in range(simulations):
        node = root

        # Selection - Traverse tree using UCB1
        while node.is_fully_expanded() and node.children:
            node = node.best_child()

        # Expansion - Add a new child node
        if not node.is_fully_expanded():
            untried_moves = [m for m in generate_moves(node.state) if m not in [child.state for child in node.children]]
            move = random.choice(untried_moves)
            new_state = apply_move(node.state, move)
            child_node = TreeNode(new_state, parent=node)
            node.children.append(child_node)
            node = child_node

        # Simulation - Instead of random, use Minimax for rollout evaluation
        value = minimax(node.state, depth_limit, float('-inf'), float('inf'), False)

        # Backpropagation
        while node:
            node.visits += 1
            node.value += value
            node = node.parent

    # Select the best move after simulations
    best_move = root.best_child(exploration_weight=0).state  # Choose child with highest avg value
    return best_move
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
        logging.basicConfig(level=logging.INFO)
    else:
        url = "http://127.0.0.1:16200/register"
        # TODO - Change logging.basicConfig if you want
        logging.basicConfig(level=logging.WARNING)

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