Serverless and Stateless
========================

Swiss Pairings app in Azure
---------------------------

This is a small example of a [Swiss Pairings](https://en.wikipedia.org/wiki/Swiss-system_tournament) tool for use in non elimination tournaments
such as that seen in a Magic the Gathering sealed event.

How does it work?
-----------------
Rather than keep a record of the event in a database, or local storage on a VM, the entire state of the tournament is encoded in the URL. This means
that a bookmark can be created or emailed and revisited at any time without losing the current standings. Tie breakers based on opponent win ratio
are taken into account.

Why is this here?
-----------------
Just for the fun, and as a demo of how serverless applications can still have a state.

How it used?
------------
Simple enter the number of players (128 max, although good luck managing a tournament with more players than that), and the number of rounds (for a
clear winner the minimum is log base 2 of the number of players)

Todo
----
Add support for dropping players

Someday one of my kids will write a nice user interface as a learning exercise ;)

