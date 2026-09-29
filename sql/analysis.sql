-- Q1: Do cheaper games get better reviews?
-- Only games with 500+ reviews, so a few early reviews don't skew the score.
SELECT
    CASE
        WHEN full_price_usd = 0 THEN '1. Free'
        WHEN full_price_usd < 10 THEN '2. Under $10'
        WHEN full_price_usd < 20 THEN '3. $10-19'
        WHEN full_price_usd < 40 THEN '4. $20-39'
        ELSE '5. $40+'
    END AS price_range,
    COUNT(*) AS games,
    ROUND(AVG(positive_pct), 1) AS avg_positive_pct
FROM games
WHERE total_reviews >= 500
GROUP BY price_range
ORDER BY price_range;

-- Q2: Which genres are most common, and which get the best reviews?
SELECT
    gg.genre,
    COUNT(*) AS games,
    ROUND(AVG(g.positive_pct), 1) AS avg_positive_pct,
    ROUND(AVG(g.owners_mid) / 1000000.0, 2) AS avg_owners_millions
FROM game_genres gg
JOIN games g ON g.appid = gg.appid
WHERE g.total_reviews >= 500
GROUP BY gg.genre
HAVING COUNT(*) >= 20
ORDER BY games DESC;

-- Q3: Which genres are growing? Top games released per genre per year since 2018.
SELECT
    g.release_year,
    gg.genre,
    COUNT(*) AS games
FROM game_genres gg
JOIN games g ON g.appid = gg.appid
WHERE g.release_year >= 2018
  AND gg.genre IN ('Action', 'Adventure', 'RPG', 'Strategy', 'Simulation', 'Indie')
GROUP BY g.release_year, gg.genre
ORDER BY gg.genre, g.release_year;

-- Q4: Is there a best month to launch a game?
SELECT
    release_month,
    COUNT(*) AS games_released,
    ROUND(AVG(positive_pct), 1) AS avg_positive_pct,
    ROUND(AVG(owners_mid) / 1000000.0, 2) AS avg_owners_millions
FROM games
WHERE release_month IS NOT NULL
GROUP BY release_month
ORDER BY release_month;
