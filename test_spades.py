import random
from spades import SpadesGame, SpadesGameState

def test_spades_game():
    game = SpadesGame()
    
    print("--- Adding Players ---")
    users = {1: "Alice", 2: "Bob"}
    for uid, name in users.items():
        game.add_player(uid, name)
        
    print(f"Players added: {game.get_player_count()}")
    
    game.start_game()
    print(f"Game State after start: {game.state}")
    
    for tid in [1, 2]:
        team_members = [users[uid] for uid in game.get_team_players(tid)]
        print(f"Team {tid}: {team_members[0]}")
        
    # Bidding
    print("\n--- Bidding Phase ---")
    for uid in game.player_ids:
        # Just random bids
        bid = random.randint(1, 4)
        game.place_bid(uid, bid)
        print(f"{users[uid]} bids {bid}")
        
    print(f"Game State after bidding: {game.state}")
    
    # Playing tricks
    print("\n--- Playing Tricks ---")
    trick_count = 1
    
    while game.state == SpadesGameState.PLAYING_TRICK:
        cp = game.current_player_id
        hand = game.hands[cp]
        valid_plays = game.get_valid_plays(hand)
        
        # Randomly play a valid card
        card_to_play = random.choice(valid_plays)
        
        success, msg, _, finished, eval_msg = game.play_card(cp, str(card_to_play))
        if success:
            print(f"{users[cp]} plays {str(card_to_play)}")
            if finished:
                print(f"Trick {trick_count} finished!")
                print(eval_msg)
                print("-" * 20)
                trick_count += 1
        else:
            print(f"ERROR: {users[cp]} failed to play {str(card_to_play)}: {msg}")
            break

    print("\n--- Final Results ---")
    print(f"Game State: {game.state}")
    if game.state == SpadesGameState.GAME_OVER:
         print(f"Winning Team: {game.winning_team}")

if __name__ == "__main__":
    test_spades_game()
