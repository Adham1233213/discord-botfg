import discord
from discord.ext import commands
import random
import asyncio
from config import Config

class GamesCog(commands.Cog):
    """Mini-games for server entertainment"""
    
    def __init__(self, bot, database):
        self.bot = bot
        self.db = database
        self.active_games = {}  # Track active games to prevent spam
    
    def check_game_cooldown(self, user_id):
        """Check if user is on game cooldown"""
        return user_id in self.active_games
    
    def add_game_cooldown(self, user_id, duration=30):
        """Add user to game cooldown"""
        self.active_games[user_id] = True
        asyncio.create_task(self.remove_cooldown(user_id, duration))
    
    async def remove_cooldown(self, user_id, duration):
        """Remove user from cooldown after duration"""
        await asyncio.sleep(duration)
        self.active_games.pop(user_id, None)
    
    @commands.command(name='gamestats')
    async def game_stats(self, ctx, member: discord.Member = None):
        """Check game statistics for a user"""
        if member is None:
            member = ctx.author
        
        try:
            stats = await self.db.get_game_stats(member.id, ctx.guild.id)
            
            if not stats:
                embed = discord.Embed(
                    title="🎮 Game Statistics",
                    description=f"{member.display_name} hasn't played any games yet!",
                    color=Config.INFO_COLOR
                )
                await ctx.send(embed=embed)
                return
            
            embed = discord.Embed(
                title=f"🎮 Game Statistics - {member.display_name}",
                color=Config.INFO_COLOR
            )
            
            total_wins = sum(stat[4] for stat in stats)  # wins column
            total_losses = sum(stat[5] for stat in stats)  # losses column
            total_points = sum(stat[6] for stat in stats)  # points column
            
            embed.add_field(name="📊 Overall Stats", 
                          value=f"**Wins:** {total_wins}\n**Losses:** {total_losses}\n**Points:** {total_points}", 
                          inline=False)
            
            for stat in stats:
                user_id, guild_id, game_name, wins, losses, points = stat
                embed.add_field(name=f"🎯 {game_name.title()}", 
                              value=f"W: {wins} | L: {losses} | P: {points}", 
                              inline=True)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")
    
    @commands.command(name='coinflip', aliases=['cf'])
    async def coin_flip(self, ctx, choice: str = None):
        """Flip a coin - guess heads or tails"""
        if self.check_game_cooldown(ctx.author.id):
            await ctx.send("⏰ You're on game cooldown! Please wait.")
            return
        
        if choice is None:
            await ctx.send("❌ Please choose heads or tails! Example: `!coinflip heads`")
            return
        
        choice = choice.lower()
        if choice not in ['heads', 'tails', 'h', 't']:
            await ctx.send("❌ Invalid choice! Use 'heads' or 'tails'")
            return
        
        # Normalize choice
        if choice in ['h', 'heads']:
            choice = 'heads'
        else:
            choice = 'tails'
        
        result = random.choice(['heads', 'tails'])
        won = choice == result
        points = 10 if won else 0
        
        embed = discord.Embed(
            title="🪙 Coin Flip",
            color=Config.SUCCESS_COLOR if won else Config.ERROR_COLOR
        )
        
        embed.add_field(name="Your Choice", value=choice.title(), inline=True)
        embed.add_field(name="Result", value=result.title(), inline=True)
        embed.add_field(name="Points", value=f"+{points}", inline=True)
        
        if won:
            embed.description = "🎉 You won!"
        else:
            embed.description = "💸 You lost!"
        
        await ctx.send(embed=embed)
        await self.db.update_game_stats(ctx.author.id, ctx.guild.id, "coinflip", won, points)
        self.add_game_cooldown(ctx.author.id, 10)
    
    @commands.command(name='dice', aliases=['roll'])
    async def dice_roll(self, ctx, guess: int = None):
        """Roll a dice - guess the number (1-6)"""
        if self.check_game_cooldown(ctx.author.id):
            await ctx.send("⏰ You're on game cooldown! Please wait.")
            return
        
        if guess is None:
            await ctx.send("❌ Please guess a number between 1 and 6! Example: `!dice 4`")
            return
        
        if guess < 1 or guess > 6:
            await ctx.send("❌ Number must be between 1 and 6!")
            return
        
        result = random.randint(1, 6)
        won = guess == result
        points = 50 if won else 0
        
        embed = discord.Embed(
            title="🎲 Dice Roll",
            color=Config.SUCCESS_COLOR if won else Config.ERROR_COLOR
        )
        
        embed.add_field(name="Your Guess", value=str(guess), inline=True)
        embed.add_field(name="Result", value=str(result), inline=True)
        embed.add_field(name="Points", value=f"+{points}", inline=True)
        
        if won:
            embed.description = "🎉 Perfect guess!"
        else:
            embed.description = "💸 Better luck next time!"
        
        await ctx.send(embed=embed)
        await self.db.update_game_stats(ctx.author.id, ctx.guild.id, "dice", won, points)
        self.add_game_cooldown(ctx.author.id, 10)
    
    @commands.command(name='rps')
    async def rock_paper_scissors(self, ctx, choice: str = None):
        """Rock Paper Scissors game"""
        if self.check_game_cooldown(ctx.author.id):
            await ctx.send("⏰ You're on game cooldown! Please wait.")
            return
        
        if choice is None:
            await ctx.send("❌ Please choose rock, paper, or scissors! Example: `!rps rock`")
            return
        
        choice = choice.lower()
        valid_choices = ['rock', 'paper', 'scissors', 'r', 'p', 's']
        
        if choice not in valid_choices:
            await ctx.send("❌ Invalid choice! Use rock, paper, or scissors")
            return
        
        # Normalize choices
        choice_map = {'r': 'rock', 'p': 'paper', 's': 'scissors'}
        if choice in choice_map:
            choice = choice_map[choice]
        
        bot_choice = random.choice(['rock', 'paper', 'scissors'])
        
        # Determine winner
        if choice == bot_choice:
            result = "tie"
            points = 5
        elif (choice == 'rock' and bot_choice == 'scissors') or \
             (choice == 'paper' and bot_choice == 'rock') or \
             (choice == 'scissors' and bot_choice == 'paper'):
            result = "win"
            points = 25
        else:
            result = "loss"
            points = 0
        
        emoji_map = {'rock': '🪨', 'paper': '📄', 'scissors': '✂️'}
        
        embed = discord.Embed(
            title="✂️ Rock Paper Scissors",
            color=Config.SUCCESS_COLOR if result == "win" else Config.WARNING_COLOR if result == "tie" else Config.ERROR_COLOR
        )
        
        embed.add_field(name="Your Choice", value=f"{emoji_map[choice]} {choice.title()}", inline=True)
        embed.add_field(name="Bot Choice", value=f"{emoji_map[bot_choice]} {bot_choice.title()}", inline=True)
        embed.add_field(name="Points", value=f"+{points}", inline=True)
        
        if result == "win":
            embed.description = "🎉 You won!"
        elif result == "tie":
            embed.description = "🤝 It's a tie!"
        else:
            embed.description = "💸 You lost!"
        
        await ctx.send(embed=embed)
        await self.db.update_game_stats(ctx.author.id, ctx.guild.id, "rps", result == "win", points)
        self.add_game_cooldown(ctx.author.id, 10)
    
    @commands.command(name='trivia')
    async def trivia_game(self, ctx):
        """Answer a trivia question"""
        if self.check_game_cooldown(ctx.author.id):
            await ctx.send("⏰ You're on game cooldown! Please wait.")
            return
        
        questions = [
            {"q": "What is the capital of France?", "a": "paris", "options": ["London", "Berlin", "Paris", "Madrid"]},
            {"q": "Which planet is known as the Red Planet?", "a": "mars", "options": ["Venus", "Mars", "Jupiter", "Saturn"]},
            {"q": "What is 2 + 2?", "a": "4", "options": ["3", "4", "5", "6"]},
            {"q": "Who painted the Mona Lisa?", "a": "leonardo da vinci", "options": ["Van Gogh", "Picasso", "Leonardo da Vinci", "Michelangelo"]},
            {"q": "What is the largest ocean on Earth?", "a": "pacific", "options": ["Atlantic", "Indian", "Pacific", "Arctic"]},
            {"q": "In which year did World War II end?", "a": "1945", "options": ["1944", "1945", "1946", "1947"]},
            {"q": "What is the chemical symbol for gold?", "a": "au", "options": ["Go", "Gd", "Au", "Ag"]},
            {"q": "Which country gifted the Statue of Liberty to the USA?", "a": "france", "options": ["Spain", "France", "Italy", "Germany"]},
        ]
        
        question_data = random.choice(questions)
        question = question_data["q"]
        correct_answer = question_data["a"]
        options = question_data["options"]
        
        embed = discord.Embed(
            title="🧠 Trivia Question",
            description=question,
            color=Config.INFO_COLOR
        )
        
        for i, option in enumerate(options, 1):
            embed.add_field(name=f"{i}.", value=option, inline=True)
        
        embed.set_footer(text="You have 30 seconds to answer! Type the number (1-4) or the answer.")
        
        message = await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            response = await self.bot.wait_for('message', check=check, timeout=30.0)
            user_answer = response.content.lower().strip()
            
            # Check if answer is correct (either by number or text)
            correct = False
            if user_answer == correct_answer:
                correct = True
            elif user_answer.isdigit():
                answer_num = int(user_answer)
                if 1 <= answer_num <= 4 and options[answer_num - 1].lower() == correct_answer:
                    correct = True
            
            points = 30 if correct else 0
            
            result_embed = discord.Embed(
                title="🧠 Trivia Result",
                color=Config.SUCCESS_COLOR if correct else Config.ERROR_COLOR
            )
            
            if correct:
                result_embed.description = "🎉 Correct answer!"
            else:
                result_embed.description = f"❌ Wrong! The correct answer was: {correct_answer.title()}"
            
            result_embed.add_field(name="Points", value=f"+{points}", inline=True)
            
            await ctx.send(embed=result_embed)
            await self.db.update_game_stats(ctx.author.id, ctx.guild.id, "trivia", correct, points)
            
        except asyncio.TimeoutError:
            timeout_embed = discord.Embed(
                title="⏰ Time's Up!",
                description=f"You didn't answer in time! The correct answer was: {correct_answer.title()}",
                color=Config.ERROR_COLOR
            )
            await ctx.send(embed=timeout_embed)
            await self.db.update_game_stats(ctx.author.id, ctx.guild.id, "trivia", False, 0)
        
        self.add_game_cooldown(ctx.author.id, 15)
    
    @commands.command(name='number')
    async def number_guessing(self, ctx, difficulty: str = "easy"):
        """Number guessing game with different difficulties"""
        if self.check_game_cooldown(ctx.author.id):
            await ctx.send("⏰ You're on game cooldown! Please wait.")
            return
        
        difficulties = {
            "easy": {"range": 10, "attempts": 3, "points": 20},
            "medium": {"range": 50, "attempts": 5, "points": 40},
            "hard": {"range": 100, "attempts": 7, "points": 60}
        }
        
        if difficulty not in difficulties:
            await ctx.send("❌ Invalid difficulty! Choose: easy, medium, or hard")
            return
        
        config = difficulties[difficulty]
        secret_number = random.randint(1, config["range"])
        attempts_left = config["attempts"]
        
        embed = discord.Embed(
            title="🔢 Number Guessing Game",
            description=f"I'm thinking of a number between 1 and {config['range']}!\nYou have {attempts_left} attempts.",
            color=Config.INFO_COLOR
        )
        embed.add_field(name="Difficulty", value=difficulty.title(), inline=True)
        embed.add_field(name="Potential Points", value=str(config["points"]), inline=True)
        
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
        
        won = False
        while attempts_left > 0:
            try:
                response = await self.bot.wait_for('message', check=check, timeout=60.0)
                guess = int(response.content)
                attempts_left -= 1
                
                if guess == secret_number:
                    won = True
                    break
                elif guess < secret_number:
                    hint = "📈 Too low!"
                else:
                    hint = "📉 Too high!"
                
                if attempts_left > 0:
                    await ctx.send(f"{hint} You have {attempts_left} attempts left.")
                
            except asyncio.TimeoutError:
                await ctx.send("⏰ Time's up! Game ended.")
                break
        
        points = config["points"] if won else 0
        
        result_embed = discord.Embed(
            title="🔢 Game Result",
            color=Config.SUCCESS_COLOR if won else Config.ERROR_COLOR
        )
        
        if won:
            result_embed.description = f"🎉 Correct! The number was {secret_number}!"
        else:
            result_embed.description = f"💸 Game over! The number was {secret_number}."
        
        result_embed.add_field(name="Points", value=f"+{points}", inline=True)
        
        await ctx.send(embed=result_embed)
        await self.db.update_game_stats(ctx.author.id, ctx.guild.id, "number_guess", won, points)
        self.add_game_cooldown(ctx.author.id, 20)
    
    @commands.command(name='slots')
    async def slot_machine(self, ctx):
        """Slot machine game"""
        if self.check_game_cooldown(ctx.author.id):
            await ctx.send("⏰ You're on game cooldown! Please wait.")
            return
        
        symbols = ['🍎', '🍊', '🍇', '🍒', '🍋', '💎', '⭐', '🔔']
        weights = [20, 20, 20, 20, 10, 5, 3, 2]  # Different probabilities
        
        result = random.choices(symbols, weights=weights, k=3)
        
        # Calculate winnings
        points = 0
        if result[0] == result[1] == result[2]:  # All three match
            if result[0] == '💎':
                points = 200
            elif result[0] == '⭐':
                points = 150
            elif result[0] == '🔔':
                points = 100
            else:
                points = 50
        elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:  # Two match
            points = 10
        
        won = points > 0
        
        embed = discord.Embed(
            title="🎰 Slot Machine",
            description=f"{''.join(result)}",
            color=Config.SUCCESS_COLOR if won else Config.ERROR_COLOR
        )
        
        if won:
            embed.add_field(name="Result", value="🎉 Winner!", inline=False)
            if points >= 100:
                embed.add_field(name="Special", value="💰 JACKPOT!", inline=True)
        else:
            embed.add_field(name="Result", value="💸 Try again!", inline=False)
        
        embed.add_field(name="Points", value=f"+{points}", inline=True)
        
        await ctx.send(embed=embed)
        await self.db.update_game_stats(ctx.author.id, ctx.guild.id, "slots", won, points)
        self.add_game_cooldown(ctx.author.id, 15)
    
    @commands.command(name='memory')
    async def memory_game(self, ctx, difficulty: str = "easy"):
        """Memory sequence game"""
        if self.check_game_cooldown(ctx.author.id):
            await ctx.send("⏰ You're on game cooldown! Please wait.")
            return
        
        difficulties = {"easy": 3, "medium": 5, "hard": 7}
        points_map = {"easy": 15, "medium": 30, "hard": 50}
        
        if difficulty not in difficulties:
            await ctx.send("❌ Invalid difficulty! Choose: easy, medium, or hard")
            return
        
        length = difficulties[difficulty]
        sequence = [random.randint(1, 9) for _ in range(length)]
        sequence_str = " ".join(map(str, sequence))
        
        embed = discord.Embed(
            title="🧠 Memory Game",
            description=f"Remember this sequence:\n\n**{sequence_str}**",
            color=Config.INFO_COLOR
        )
        embed.add_field(name="Instructions", value="You have 10 seconds to memorize, then type it back!", inline=False)
        embed.add_field(name="Difficulty", value=difficulty.title(), inline=True)
        
        await ctx.send(embed=embed)
        await asyncio.sleep(10)
        
        await ctx.send("⏰ Time's up! Now type the sequence back (numbers separated by spaces):")
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            response = await self.bot.wait_for('message', check=check, timeout=30.0)
            user_sequence = response.content.strip().split()
            
            correct = user_sequence == [str(x) for x in sequence]
            points = points_map[difficulty] if correct else 0
            
            result_embed = discord.Embed(
                title="🧠 Memory Result",
                color=Config.SUCCESS_COLOR if correct else Config.ERROR_COLOR
            )
            
            if correct:
                result_embed.description = "🎉 Perfect memory!"
            else:
                result_embed.description = f"❌ Wrong! The sequence was: {sequence_str}"
            
            result_embed.add_field(name="Your Answer", value=" ".join(user_sequence), inline=True)
            result_embed.add_field(name="Correct Answer", value=sequence_str, inline=True)
            result_embed.add_field(name="Points", value=f"+{points}", inline=True)
            
            await ctx.send(embed=result_embed)
            await self.db.update_game_stats(ctx.author.id, ctx.guild.id, "memory", correct, points)
            
        except asyncio.TimeoutError:
            timeout_embed = discord.Embed(
                title="⏰ Time's Up!",
                description=f"You didn't answer in time! The sequence was: {sequence_str}",
                color=Config.ERROR_COLOR
            )
            await ctx.send(embed=timeout_embed)
            await self.db.update_game_stats(ctx.author.id, ctx.guild.id, "memory", False, 0)
        
        self.add_game_cooldown(ctx.author.id, 20)
    
    @commands.command(name='riddle')
    async def riddle_game(self, ctx):
        """Solve a riddle"""
        if self.check_game_cooldown(ctx.author.id):
            await ctx.send("⏰ You're on game cooldown! Please wait.")
            return
        
        riddles = [
            {"q": "What has keys but no locks, space but no room, you can enter but not go inside?", "a": "keyboard"},
            {"q": "What gets wet while drying?", "a": "towel"},
            {"q": "What can travel around the world while staying in a corner?", "a": "stamp"},
            {"q": "What has hands but cannot clap?", "a": "clock"},
            {"q": "What has a head, a tail, but no body?", "a": "coin"},
            {"q": "What goes up but never comes down?", "a": "age"},
            {"q": "What can you catch but not throw?", "a": "cold"},
            {"q": "What has an eye but cannot see?", "a": "needle"},
        ]
        
        riddle = random.choice(riddles)
        
        embed = discord.Embed(
            title="🤔 Riddle Time",
            description=riddle["q"],
            color=Config.INFO_COLOR
        )
        embed.set_footer(text="You have 60 seconds to answer!")
        
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            response = await self.bot.wait_for('message', check=check, timeout=60.0)
            user_answer = response.content.lower().strip()
            
            correct = user_answer == riddle["a"]
            points = 35 if correct else 0
            
            result_embed = discord.Embed(
                title="🤔 Riddle Result",
                color=Config.SUCCESS_COLOR if correct else Config.ERROR_COLOR
            )
            
            if correct:
                result_embed.description = "🎉 Correct! Great thinking!"
            else:
                result_embed.description = f"❌ Wrong! The answer was: {riddle['a']}"
            
            result_embed.add_field(name="Points", value=f"+{points}", inline=True)
            
            await ctx.send(embed=result_embed)
            await self.db.update_game_stats(ctx.author.id, ctx.guild.id, "riddle", correct, points)
            
        except asyncio.TimeoutError:
            timeout_embed = discord.Embed(
                title="⏰ Time's Up!",
                description=f"You didn't answer in time! The answer was: {riddle['a']}",
                color=Config.ERROR_COLOR
            )
            await ctx.send(embed=timeout_embed)
            await self.db.update_game_stats(ctx.author.id, ctx.guild.id, "riddle", False, 0)
        
        self.add_game_cooldown(ctx.author.id, 20)
    
    @commands.command(name='math')
    async def math_game(self, ctx, difficulty: str = "easy"):
        """Solve a math problem"""
        if self.check_game_cooldown(ctx.author.id):
            await ctx.send("⏰ You're on game cooldown! Please wait.")
            return
        
        if difficulty == "easy":
            a, b = random.randint(1, 20), random.randint(1, 20)
            operation = random.choice(['+', '-'])
            if operation == '+':
                answer = a + b
                problem = f"{a} + {b}"
            else:
                answer = a - b
                problem = f"{a} - {b}"
            points = 20
        elif difficulty == "medium":
            a, b = random.randint(1, 15), random.randint(1, 15)
            operation = random.choice(['+', '-', '*', '/'])
            if operation == '+':
                answer = a + b
                problem = f"{a} + {b}"
            elif operation == '-':
                answer = a - b
                problem = f"{a} - {b}"
            elif operation == '*':
                answer = a * b
                problem = f"{a} × {b}"
            else:  # division
                answer = a
                a = a * b  # Make sure division is clean
                problem = f"{a} ÷ {b}"
            points = 35
        elif difficulty == "hard":
            a, b, c = random.randint(1, 10), random.randint(1, 10), random.randint(1, 10)
            problem_type = random.choice(['square', 'mixed'])
            if problem_type == 'square':
                a = random.randint(1, 12)
                answer = a * a
                problem = f"{a}²"
            else:
                answer = (a + b) * c
                problem = f"({a} + {b}) × {c}"
            points = 50
        else:
            await ctx.send("❌ Invalid difficulty! Choose: easy, medium, or hard")
            return
        
        embed = discord.Embed(
            title="🔢 Math Challenge",
            description=f"**{problem} = ?**",
            color=Config.INFO_COLOR
        )
        embed.add_field(name="Difficulty", value=difficulty.title(), inline=True)
        embed.add_field(name="Potential Points", value=str(points), inline=True)
        embed.set_footer(text="You have 30 seconds to answer!")
        
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            response = await self.bot.wait_for('message', check=check, timeout=30.0)
            try:
                user_answer = int(response.content.strip())
                correct = user_answer == answer
                earned_points = points if correct else 0
                
                result_embed = discord.Embed(
                    title="🔢 Math Result",
                    color=Config.SUCCESS_COLOR if correct else Config.ERROR_COLOR
                )
                
                if correct:
                    result_embed.description = "🎉 Correct! Great math skills!"
                else:
                    result_embed.description = f"❌ Wrong! The answer was: {answer}"
                
                result_embed.add_field(name="Your Answer", value=str(user_answer), inline=True)
                result_embed.add_field(name="Correct Answer", value=str(answer), inline=True)
                result_embed.add_field(name="Points", value=f"+{earned_points}", inline=True)
                
                await ctx.send(embed=result_embed)
                await self.db.update_game_stats(ctx.author.id, ctx.guild.id, "math", correct, earned_points)
                
            except ValueError:
                await ctx.send("❌ Please enter a valid number!")
                await self.db.update_game_stats(ctx.author.id, ctx.guild.id, "math", False, 0)
            
        except asyncio.TimeoutError:
            timeout_embed = discord.Embed(
                title="⏰ Time's Up!",
                description=f"You didn't answer in time! The answer was: {answer}",
                color=Config.ERROR_COLOR
            )
            await ctx.send(embed=timeout_embed)
            await self.db.update_game_stats(ctx.author.id, ctx.guild.id, "math", False, 0)
        
        self.add_game_cooldown(ctx.author.id, 15)
    
    @commands.command(name='wordscramble', aliases=['scramble'])
    async def word_scramble(self, ctx):
        """Unscramble a word"""
        if self.check_game_cooldown(ctx.author.id):
            await ctx.send("⏰ You're on game cooldown! Please wait.")
            return
        
        words = [
            "python", "discord", "computer", "keyboard", "monitor", "mouse", "programming",
            "database", "internet", "website", "server", "network", "software", "hardware",
            "algorithm", "function", "variable", "string", "integer", "boolean"
        ]
        
        word = random.choice(words)
        scrambled = ''.join(random.sample(word, len(word)))
        
        # Make sure it's actually scrambled
        while scrambled == word:
            scrambled = ''.join(random.sample(word, len(word)))
        
        embed = discord.Embed(
            title="🔤 Word Scramble",
            description=f"Unscramble this word:\n\n**{scrambled.upper()}**",
            color=Config.INFO_COLOR
        )
        embed.add_field(name="Hint", value=f"It's {len(word)} letters long!", inline=True)
        embed.set_footer(text="You have 45 seconds to answer!")
        
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            response = await self.bot.wait_for('message', check=check, timeout=45.0)
            user_answer = response.content.lower().strip()
            
            correct = user_answer == word
            points = 25 if correct else 0
            
            result_embed = discord.Embed(
                title="🔤 Scramble Result",
                color=Config.SUCCESS_COLOR if correct else Config.ERROR_COLOR
            )
            
            if correct:
                result_embed.description = "🎉 Correct! Well unscrambled!"
            else:
                result_embed.description = f"❌ Wrong! The word was: {word}"
            
            result_embed.add_field(name="Scrambled", value=scrambled.upper(), inline=True)
            result_embed.add_field(name="Answer", value=word.upper(), inline=True)
            result_embed.add_field(name="Points", value=f"+{points}", inline=True)
            
            await ctx.send(embed=result_embed)
            await self.db.update_game_stats(ctx.author.id, ctx.guild.id, "word_scramble", correct, points)
            
        except asyncio.TimeoutError:
            timeout_embed = discord.Embed(
                title="⏰ Time's Up!",
                description=f"You didn't answer in time! The word was: {word}",
                color=Config.ERROR_COLOR
            )
            await ctx.send(embed=timeout_embed)
            await self.db.update_game_stats(ctx.author.id, ctx.guild.id, "word_scramble", False, 0)
        
        self.add_game_cooldown(ctx.author.id, 15)
    
    @commands.command(name='reaction')
    async def reaction_game(self, ctx):
        """Test your reaction time"""
        if self.check_game_cooldown(ctx.author.id):
            await ctx.send("⏰ You're on game cooldown! Please wait.")
            return
        
        embed = discord.Embed(
            title="⚡ Reaction Test",
            description="Click the ⚡ reaction when it appears!",
            color=Config.INFO_COLOR
        )
        embed.add_field(name="Instructions", value="Wait for the lightning bolt emoji to appear, then click it as fast as you can!", inline=False)
        
        message = await ctx.send(embed=embed)
        
        # Wait random time between 2-8 seconds
        wait_time = random.uniform(2.0, 8.0)
        await asyncio.sleep(wait_time)
        
        # Add the reaction
        start_time = asyncio.get_event_loop().time()
        await message.add_reaction('⚡')
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == '⚡' and reaction.message.id == message.id
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout=5.0)
            end_time = asyncio.get_event_loop().time()
            reaction_time = round((end_time - start_time) * 1000)  # Convert to milliseconds
            
            # Score based on reaction time
            if reaction_time < 200:
                score = "🏆 AMAZING!"
                points = 100
            elif reaction_time < 300:
                score = "🥇 EXCELLENT!"
                points = 75
            elif reaction_time < 500:
                score = "🥈 GREAT!"
                points = 50
            elif reaction_time < 800:
                score = "🥉 GOOD!"
                points = 25
            else:
                score = "👍 Nice try!"
                points = 10
            
            result_embed = discord.Embed(
                title="⚡ Reaction Result",
                description=f"{score}",
                color=Config.SUCCESS_COLOR
            )
            result_embed.add_field(name="Reaction Time", value=f"{reaction_time}ms", inline=True)
            result_embed.add_field(name="Points", value=f"+{points}", inline=True)
            
            await ctx.send(embed=result_embed)
            await self.db.update_game_stats(ctx.author.id, ctx.guild.id, "reaction", True, points)
            
        except asyncio.TimeoutError:
            timeout_embed = discord.Embed(
                title="⏰ Too Slow!",
                description="You didn't react in time! Try to be faster next time.",
                color=Config.ERROR_COLOR
            )
            await ctx.send(embed=timeout_embed)
            await self.db.update_game_stats(ctx.author.id, ctx.guild.id, "reaction", False, 0)
        
        self.add_game_cooldown(ctx.author.id, 30)
    
    @commands.command(name='games')
    async def list_games(self, ctx):
        """List all available games"""
        embed = discord.Embed(
            title="🎮 Available Games",
            description="Here are all the games you can play:",
            color=Config.INFO_COLOR
        )
        
        games = [
            "🪙 `!coinflip heads/tails` - Guess heads or tails (10 pts)",
            "🎲 `!dice 1-6` - Guess the dice roll (50 pts)",
            "✂️ `!rps rock/paper/scissors` - Rock Paper Scissors (25 pts)",
            "🧠 `!trivia` - Answer trivia questions (30 pts)",
            "🔢 `!number easy/medium/hard` - Number guessing game (20-60 pts)",
            "🎰 `!slots` - Slot machine game (up to 200 pts)",
            "🧠 `!memory easy/medium/hard` - Memory sequence game (15-50 pts)",
            "🤔 `!riddle` - Solve riddles (35 pts)",
            "🔢 `!math easy/medium/hard` - Math problems (20-50 pts)",
            "🔤 `!wordscramble` - Unscramble words (25 pts)",
            "⚡ `!reaction` - Reaction time test (10-100 pts)",
            "📊 `!gamestats` - Check your game statistics"
        ]
        
        embed.add_field(name="🎯 Game List", value="\n".join(games), inline=False)
        embed.add_field(name="💡 Tips", 
                      value="• Games have cooldowns to prevent spam\n• Points are tracked in your statistics\n• Some games have difficulty levels", 
                      inline=False)
        
        await ctx.send(embed=embed)