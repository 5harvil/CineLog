
# ============================================================
# CINELOG - PERSONAL MOVIE DIARY
# Batch 1: Setup, database connection and user authentication
# ============================================================

import mysql.connector
import hashlib
import secrets
import random


# -------------------- DATABASE CONFIGURATION -----------------

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "groots",
    "database": "cinelog_db"
}


# -------------------- DATABASE CONNECTION --------------------

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    print("\nDatabase connected successfully!")
except mysql.connector.Error as err:
    print("\nCould not connect to MySQL:", err)
    print("Check your MySQL server and DB_CONFIG settings.")
    raise SystemExit


# -------------------- DISPLAY UTILITIES ----------------------

def line():
    print("=" * 58)


def heading(title):
    print()
    line()
    print(title.center(58))
    line()


def pause():
    input("\nPress ENTER to continue...")


def get_rating():
    while True:
        try:
            rating = int(input("Enter your rating (1-5): "))
            if 1 <= rating <= 5:
                return rating
            print("Rating must be between 1 and 5.")
        except ValueError:
            print("Please enter a whole number.")


def get_nonempty(prompt, max_length):
    while True:
        value = input(prompt).strip()

        if not value:
            print("This field cannot be empty.")
        elif len(value) > max_length:
            print("Maximum length is", max_length, "characters.")
        else:
            return value


# -------------------- PASSWORD SECURITY ----------------------

def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        200000
    ).hex()

    return salt + "$" + password_hash


def verify_password(password, stored_hash):
    try:
        salt, original_hash = stored_hash.split("$")
        new_hash = hash_password(password, salt)
        return secrets.compare_digest(
            new_hash.split("$")[1], original_hash
        )
    except (ValueError, TypeError):
        return False


# -------------------- USER REGISTRATION ----------------------

def register():
    heading("CREATE YOUR CINELOG ACCOUNT")

    username = get_nonempty("Choose a username: ", 50)

    password = get_nonempty("Choose a password: ", 100)
    confirm = input("Confirm password: ")

    if password != confirm:
        print("\nPasswords do not match.")
        pause()
        return

    try:
        cursor.execute(
            "SELECT user_id FROM users WHERE username = %s",
            (username,)
        )

        if cursor.fetchone():
            print("\nThat username already exists.")
            pause()
            return

        encrypted_password = hash_password(password)

        cursor.execute(
            "INSERT INTO users (username, password) "
            "VALUES (%s, %s)",
            (username, encrypted_password)
        )

        conn.commit()
        print("\nAccount created successfully!")
        print("You can now log in to CineLog.")

    except mysql.connector.Error as err:
        conn.rollback()
        print("\nCould not create account:", err)

    pause()


# -------------------- USER LOGIN -----------------------------

def login():
    heading("LOG IN TO CINELOG")

    username = get_nonempty("Username: ", 50)
    password = input("Password: ")

    try:
        cursor.execute(
            "SELECT user_id, username, password "
            "FROM users WHERE username = %s",
            (username,)
        )

        user = cursor.fetchone()

        if user and verify_password(password, user["password"]):
            print("\nWelcome back,", user["username"] + "!")
            return {
                "user_id": user["user_id"],
                "username": user["username"]
            }

        print("\nInvalid username or password.")

    except mysql.connector.Error as err:
        print("\nLogin error:", err)

    pause()
    return None


# ============================================================
# Batch 2: Movie diary, search, Top 3 and statistics
# ============================================================


# -------------------- SAVE A MOVIE ---------------------------

def save_movie(user_id, movie_name, director, rating):
    """Add a movie or update its rating if already present."""

    cursor.execute(
        "SELECT movie_id FROM movies "
        "WHERE user_id = %s AND LOWER(movie_name) = LOWER(%s)",
        (user_id, movie_name)
    )

    existing = cursor.fetchone()

    if existing:
        cursor.execute(
            "UPDATE movies SET director = %s, rating = %s "
            "WHERE movie_id = %s AND user_id = %s",
            (director, rating, existing["movie_id"], user_id)
        )
    else:
        cursor.execute(
            "INSERT INTO movies "
            "(user_id, movie_name, director, rating) "
            "VALUES (%s, %s, %s, %s)",
            (user_id, movie_name, director, rating)
        )

    conn.commit()


# -------------------- VIEW MY MOVIES -------------------------

def view_movies(user_id):
    heading("MY MOVIES")

    cursor.execute(
        "SELECT movie_id, movie_name, director, rating, date_added "
        "FROM movies WHERE user_id = %s "
        "ORDER BY movie_name",
        (user_id,)
    )

    movies = cursor.fetchall()

    if not movies:
        print("Your diary is empty. Add your first movie!")
    else:
        for movie in movies:
            print("\nID:", movie["movie_id"])
            print("Title:", movie["movie_name"])
            print("Director:", movie["director"])
            print("Rating:", str(movie["rating"]) + "/5")
            print("Date added:", movie["date_added"])
            print("-" * 40)

    pause()


# -------------------- ADD A MOVIE ----------------------------

def add_movie(user_id):
    heading("ADD A MOVIE")

    movie_name = get_nonempty("Movie name: ", 100)
    director = get_nonempty("Director: ", 100)
    rating = get_rating()

    try:
        save_movie(user_id, movie_name, director, rating)
        print("\nMovie saved to your diary!")

    except mysql.connector.Error as err:
        conn.rollback()
        print("\nCould not save movie:", err)

    pause()


# -------------------- EDIT A RATING --------------------------

def edit_rating(user_id):
    heading("EDIT A MOVIE RATING")

    try:
        cursor.execute(
            "SELECT movie_id, movie_name, rating FROM movies "
            "WHERE user_id = %s ORDER BY movie_name",
            (user_id,)
        )

        movies = cursor.fetchall()

        if not movies:
            print("Your diary is empty.")
            pause()
            return

        for movie in movies:
            print(
                str(movie["movie_id"]) + ".",
                movie["movie_name"],
                "| Rating:", str(movie["rating"]) + "/5"
            )

        movie_id = int(input("\nEnter the movie ID to edit: "))

        cursor.execute(
            "SELECT movie_id, movie_name FROM movies "
            "WHERE movie_id = %s AND user_id = %s",
            (movie_id, user_id)
        )

        movie = cursor.fetchone()

        if not movie:
            print("Invalid movie ID.")
        else:
            rating = get_rating()

            cursor.execute(
                "UPDATE movies SET rating = %s "
                "WHERE movie_id = %s AND user_id = %s",
                (rating, movie_id, user_id)
            )

            conn.commit()
            print("Rating updated successfully!")

    except ValueError:
        print("Please enter a valid numeric movie ID.")
    except mysql.connector.Error as err:
        conn.rollback()
        print("Could not update rating:", err)

    pause()


# -------------------- DELETE A MOVIE -------------------------

def delete_movie(user_id):
    heading("DELETE A MOVIE")

    try:
        cursor.execute(
            "SELECT movie_id, movie_name FROM movies "
            "WHERE user_id = %s ORDER BY movie_name",
            (user_id,)
        )

        movies = cursor.fetchall()

        if not movies:
            print("Your diary is empty.")
            pause()
            return

        for movie in movies:
            print(str(movie["movie_id"]) + ".", movie["movie_name"])

        movie_id = int(input("\nEnter the movie ID to delete: "))

        cursor.execute(
            "SELECT movie_name FROM movies "
            "WHERE movie_id = %s AND user_id = %s",
            (movie_id, user_id)
        )

        movie = cursor.fetchone()

        if not movie:
            print("Invalid movie ID.")
        else:
            confirm = input(
                "Delete '" + movie["movie_name"] + "'? (Y/N): "
            ).strip().upper()

            if confirm == "Y":
                cursor.execute(
                    "DELETE FROM movies "
                    "WHERE movie_id = %s AND user_id = %s",
                    (movie_id, user_id)
                )
                conn.commit()
                print("Movie deleted.")
            else:
                print("Deletion cancelled.")

    except ValueError:
        print("Please enter a valid numeric movie ID.")
    except mysql.connector.Error as err:
        conn.rollback()
        print("Could not delete movie:", err)

    pause()


# -------------------- MY MOVIES MENU -------------------------

def my_movies(user_id):
    while True:
        heading("MY MOVIES")

        print("1. View all movies")
        print("2. Add a movie")
        print("3. Edit a rating")
        print("4. Delete a movie")
        print("5. Return to main menu")

        choice = input("\nChoose an option: ").strip()

        if choice == "1":
            view_movies(user_id)
        elif choice == "2":
            add_movie(user_id)
        elif choice == "3":
            edit_rating(user_id)
        elif choice == "4":
            delete_movie(user_id)
        elif choice == "5":
            break
        else:
            print("Invalid choice. Please try again.")


# -------------------- SEARCH MOVIES --------------------------

def search_movies(user_id):
    heading("SEARCH MOVIES")

    print("1. Search by movie name")
    print("2. Search by director")

    choice = input("\nChoose a search type: ").strip()

    if choice not in ("1", "2"):
        print("Invalid choice.")
        pause()
        return

    keyword = get_nonempty("Enter your search term: ", 100)
    column = "movie_name" if choice == "1" else "director"

    query = (
        "SELECT movie_name, director, rating FROM movies "
        "WHERE user_id = %s AND " + column + " LIKE %s "
        "ORDER BY movie_name"
    )

    try:
        cursor.execute(query, (user_id, "%" + keyword + "%"))
        results = cursor.fetchall()

        if not results:
            print("\nNo matching movies found.")
        else:
            print("\nSearch results:")
            for movie in results:
                print(
                    movie["movie_name"], "|",
                    movie["director"], "|",
                    str(movie["rating"]) + "/5"
                )

    except mysql.connector.Error as err:
        print("Search failed:", err)

    pause()


# -------------------- MY TOP 3 --------------------------------

def top_three(user_id):
    heading("YOUR TOP 3 MOVIES")

    cursor.execute(
        "SELECT movie_name, director, rating FROM movies "
        "WHERE user_id = %s "
        "ORDER BY rating DESC, movie_name ASC LIMIT 3",
        (user_id,)
    )

    movies = cursor.fetchall()

    if not movies:
        print("Rate some movies to discover your Top 3!")
    else:
        for position, movie in enumerate(movies, start=1):
            print(
                "\n" + str(position) + ". " + movie["movie_name"]
            )
            print("   Director:", movie["director"])
            print("   Rating:", str(movie["rating"]) + "/5")

    pause()


# -------------------- CINESTATS -------------------------------

def cine_stats(user_id):
    heading("CINESTATS")

    cursor.execute(
        "SELECT COUNT(*) AS total, "
        "ROUND(AVG(rating), 2) AS average_rating, "
        "SUM(rating = 5) AS five_star "
        "FROM movies WHERE user_id = %s",
        (user_id,)
    )

    stats = cursor.fetchone()

    print("Movies in your diary:", stats["total"])
    print("Average rating:", stats["average_rating"] or 0, "/5")
    print("Five-star movies:", stats["five_star"] or 0)

    cursor.execute(
        "SELECT COUNT(*) AS total FROM watchlist WHERE user_id = %s",
        (user_id,)
    )

    watchlist_stats = cursor.fetchone()
    print("Movies on your watchlist:", watchlist_stats["total"])

    pause()


# ============================================================
# Batch 3: Watchlist, Movie of the Day and main program
# ============================================================


# -------------------- VIEW WATCHLIST -------------------------

def view_watchlist(user_id):
    heading("MY WATCHLIST")

    cursor.execute(
        "SELECT watchlist_id, movie_name, director, date_added "
        "FROM watchlist WHERE user_id = %s ORDER BY movie_name",
        (user_id,)
    )

    movies = cursor.fetchall()

    if not movies:
        print("Your watchlist is empty. Add a movie for later!")
    else:
        for movie in movies:
            print("\nID:", movie["watchlist_id"])
            print("Title:", movie["movie_name"])
            print("Director:", movie["director"])
            print("Added:", movie["date_added"])
            print("-" * 40)

    pause()


# -------------------- ADD TO WATCHLIST -----------------------

def add_to_watchlist(user_id):
    heading("ADD TO WATCHLIST")

    movie_name = get_nonempty("Movie name: ", 100)
    director = get_nonempty("Director: ", 100)

    try:
        cursor.execute(
            "SELECT movie_id FROM movies "
            "WHERE user_id = %s AND LOWER(movie_name) = LOWER(%s)",
            (user_id, movie_name)
        )

        if cursor.fetchone():
            print("This movie is already in your watched collection.")
            pause()
            return

        cursor.execute(
            "INSERT INTO watchlist (user_id, movie_name, director) "
            "VALUES (%s, %s, %s)",
            (user_id, movie_name, director)
        )

        conn.commit()
        print("\nAdded to your watchlist!")

    except mysql.connector.IntegrityError:
        conn.rollback()
        print("This movie is already on your watchlist.")
    except mysql.connector.Error as err:
        conn.rollback()
        print("Could not add movie:", err)

    pause()


# -------------------- MARK AS WATCHED ------------------------

def mark_as_watched(user_id):
    heading("MARK A MOVIE AS WATCHED")

    try:
        cursor.execute(
            "SELECT watchlist_id, movie_name, director "
            "FROM watchlist WHERE user_id = %s "
            "ORDER BY movie_name",
            (user_id,)
        )

        movies = cursor.fetchall()

        if not movies:
            print("Your watchlist is empty.")
            pause()
            return

        for movie in movies:
            print(
                str(movie["watchlist_id"]) + ".",
                movie["movie_name"], "-", movie["director"]
            )

        watchlist_id = int(input("\nEnter the watchlist ID: "))

        cursor.execute(
            "SELECT watchlist_id, movie_name, director "
            "FROM watchlist WHERE watchlist_id = %s "
            "AND user_id = %s",
            (watchlist_id, user_id)
        )

        movie = cursor.fetchone()

        if not movie:
            print("Invalid watchlist ID.")
            pause()
            return

        rating = get_rating()

        save_movie(
            user_id,
            movie["movie_name"],
            movie["director"],
            rating
        )

        cursor.execute(
            "DELETE FROM watchlist "
            "WHERE watchlist_id = %s AND user_id = %s",
            (watchlist_id, user_id)
        )

        conn.commit()
        print("\nMovie moved to My Movies!")
        print("Your rating:", rating, "/5")
        print("Your Top 3 and CineStats will reflect the change.")

    except ValueError:
        conn.rollback()
        print("Please enter a valid numeric ID.")
    except mysql.connector.Error as err:
        conn.rollback()
        print("Could not update your collections:", err)

    pause()


# -------------------- REMOVE FROM WATCHLIST ------------------

def remove_from_watchlist(user_id):
    heading("REMOVE FROM WATCHLIST")

    try:
        cursor.execute(
            "SELECT watchlist_id, movie_name FROM watchlist "
            "WHERE user_id = %s ORDER BY movie_name",
            (user_id,)
        )

        movies = cursor.fetchall()

        if not movies:
            print("Your watchlist is empty.")
            pause()
            return

        for movie in movies:
            print(str(movie["watchlist_id"]) + ".", movie["movie_name"])

        watchlist_id = int(input("\nEnter the ID to remove: "))

        cursor.execute(
            "SELECT movie_name FROM watchlist "
            "WHERE watchlist_id = %s AND user_id = %s",
            (watchlist_id, user_id)
        )

        movie = cursor.fetchone()

        if not movie:
            print("Invalid watchlist ID.")
        else:
            cursor.execute(
                "DELETE FROM watchlist "
                "WHERE watchlist_id = %s AND user_id = %s",
                (watchlist_id, user_id)
            )

            conn.commit()
            print("Removed", movie["movie_name"], "from your watchlist.")

    except ValueError:
        print("Please enter a valid numeric ID.")
    except mysql.connector.Error as err:
        conn.rollback()
        print("Could not remove movie:", err)

    pause()


# -------------------- WATCHLIST MENU -------------------------

def watchlist_menu(user_id):
    while True:
        heading("MY WATCHLIST")

        print("1. View watchlist")
        print("2. Add a movie")
        print("3. Mark a movie as watched")
        print("4. Remove a movie")
        print("5. Return to main menu")

        choice = input("\nChoose an option: ").strip()

        if choice == "1":
            view_watchlist(user_id)
        elif choice == "2":
            add_to_watchlist(user_id)
        elif choice == "3":
            mark_as_watched(user_id)
        elif choice == "4":
            remove_from_watchlist(user_id)
        elif choice == "5":
            break
        else:
            print("Invalid choice. Please try again.")


# -------------------- MOVIE OF THE DAY -----------------------

def movie_of_the_day(user_id):
    try:
        cursor.execute(
            "SELECT movie_name, director, rating "
            "FROM movies WHERE user_id = %s",
            (user_id,)
        )

        watched = cursor.fetchall()

        cursor.execute(
            "SELECT movie_name, director FROM watchlist "
            "WHERE user_id = %s",
            (user_id,)
        )

        watchlist = cursor.fetchall()

        # Combine both lists without duplicate movie titles.
        pool = []
        seen_titles = set()

        for movie in watched:
            title_key = movie["movie_name"].casefold()

            if title_key not in seen_titles:
                movie["status"] = "Watched"
                pool.append(movie)
                seen_titles.add(title_key)

        for movie in watchlist:
            title_key = movie["movie_name"].casefold()

            if title_key not in seen_titles:
                movie["status"] = "On your watchlist"
                pool.append(movie)
                seen_titles.add(title_key)

        # Do not display a prompt if both collections are empty.
        if not pool:
            return

        movie = random.choice(pool)

        heading("TONIGHT'S PICK")

        print('"' + movie["movie_name"] + '"')
        print("Director:", movie["director"])
        print("Collection:", movie["status"])

        if movie["status"] == "Watched":
            print("Your rating:", str(movie["rating"]) + "/5")
            prompt = "Fancy a rewatch? (Y/N): "
        else:
            print("A film waiting for you to discover it!")
            prompt = "Want to watch it and rate it now? (Y/N): "

        choice = input("\n" + prompt).strip().upper()

        if choice == "Y":
            if movie["status"] == "On your watchlist":
                cursor.execute(
                    "SELECT watchlist_id FROM watchlist "
                    "WHERE user_id = %s "
                    "AND LOWER(movie_name) = LOWER(%s)",
                    (user_id, movie["movie_name"])
                )

                entry = cursor.fetchone()

                if entry:
                    rating = get_rating()

                    save_movie(
                        user_id,
                        movie["movie_name"],
                        movie["director"],
                        rating
                    )

                    cursor.execute(
                        "DELETE FROM watchlist "
                        "WHERE watchlist_id = %s AND user_id = %s",
                        (entry["watchlist_id"], user_id)
                    )

                    conn.commit()
                    print("Movie added to My Movies with your rating!")
                else:
                    print("This watchlist entry no longer exists.")

            else:
                print("Enjoy revisiting your favourite film!")
                print("You can change its rating in My Movies.")

        else:
            print("Enjoy exploring your movie universe!")

    except mysql.connector.Error as err:
        conn.rollback()
        print("Movie of the Day could not load:", err)


# -------------------- MAIN MENU ------------------------------

def main_menu(user):
    user_id = user["user_id"]

    # Automatically suggest a film after login.
    movie_of_the_day(user_id)

    while True:
        heading("CINELOG | MAIN MENU")

        print("Welcome,", user["username"])
        print()
        print("1. My Movies")
        print("2. Search Movies")
        print("3. My Top 3")
        print("4. CineStats")
        print("5. My Watchlist")
        print("6. Log Out")

        choice = input("\nChoose an option: ").strip()

        if choice == "1":
            my_movies(user_id)
        elif choice == "2":
            search_movies(user_id)
        elif choice == "3":
            top_three(user_id)
        elif choice == "4":
            cine_stats(user_id)
        elif choice == "5":
            watchlist_menu(user_id)
        elif choice == "6":
            print("\nLogged out successfully.")
            break
        else:
            print("Invalid choice. Please try again.")


# -------------------- START THE PROGRAM ---------------------

def main():
    while True:
        heading("CINELOG")
        print("Every film leaves a mark.\n")
        print("1. Register")
        print("2. Log In")
        print("3. Exit")

        choice = input("\nChoose an option: ").strip()

        if choice == "1":
            register()

        elif choice == "2":
            user = login()

            if user:
                main_menu(user)

        elif choice == "3":
            print("\nThanks for using CineLog. Goodbye!")
            break

        else:
            print("Invalid choice. Please try again.")


try:
    main()
finally:
    cursor.close()
    conn.close()
    print("\nDatabase connection closed.")

