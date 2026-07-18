-- SiteRegistry.db schema (SQLite STRICT)
-- One table per category. type_url is ANY (polymorphic: list/str/Redirect as
-- JSON text), info is TEXT (JSON or NULL), reverse_condition is INTEGER (0/1).
-- Generated from the live DB.

CREATE TABLE SOCIAL (
    link TEXT NOT NULL UNIQUE,
    info TEXT,
    type_url ANY,
    reverse_condition INTEGER NOT NULL DEFAULT 0
) STRICT;
CREATE UNIQUE INDEX idx_SOCIAL_link ON SOCIAL(link);

CREATE TABLE FORUMS (
    link TEXT NOT NULL UNIQUE,
    info TEXT,
    type_url ANY,
    reverse_condition INTEGER NOT NULL DEFAULT 0
) STRICT;
CREATE UNIQUE INDEX idx_FORUMS_link ON FORUMS(link);

CREATE TABLE BLOGS (
    link TEXT NOT NULL UNIQUE,
    info TEXT,
    type_url ANY,
    reverse_condition INTEGER NOT NULL DEFAULT 0
) STRICT;
CREATE UNIQUE INDEX idx_BLOGS_link ON BLOGS(link);

CREATE TABLE GAMING (
    link TEXT NOT NULL UNIQUE,
    info TEXT,
    type_url ANY,
    reverse_condition INTEGER NOT NULL DEFAULT 0
) STRICT;
CREATE UNIQUE INDEX idx_GAMING_link ON GAMING(link);

CREATE TABLE DEV (
    link TEXT NOT NULL UNIQUE,
    info TEXT,
    type_url ANY,
    reverse_condition INTEGER NOT NULL DEFAULT 0
) STRICT;
CREATE UNIQUE INDEX idx_DEV_link ON DEV(link);

CREATE TABLE CREATIVE (
    link TEXT NOT NULL UNIQUE,
    info TEXT,
    type_url ANY,
    reverse_condition INTEGER NOT NULL DEFAULT 0
) STRICT;
CREATE UNIQUE INDEX idx_CREATIVE_link ON CREATIVE(link);

CREATE TABLE MISC (
    link TEXT NOT NULL UNIQUE,
    info TEXT,
    type_url ANY,
    reverse_condition INTEGER NOT NULL DEFAULT 0
) STRICT;
CREATE UNIQUE INDEX idx_MISC_link ON MISC(link);

CREATE TABLE PROFESSIONAL (
    link TEXT NOT NULL UNIQUE,
    info TEXT,
    type_url ANY,
    reverse_condition INTEGER NOT NULL DEFAULT 0
) STRICT;
CREATE UNIQUE INDEX idx_PROFESSIONAL_link ON PROFESSIONAL(link);

CREATE TABLE PEOPLE_SEARCH (
    link TEXT NOT NULL UNIQUE,
    info TEXT,
    type_url ANY,
    reverse_condition INTEGER NOT NULL DEFAULT 0
) STRICT;
CREATE UNIQUE INDEX idx_PEOPLE_SEARCH_link ON PEOPLE_SEARCH(link);

CREATE TABLE LINKS (
    link TEXT NOT NULL UNIQUE,
    info TEXT,
    type_url ANY,
    reverse_condition INTEGER NOT NULL DEFAULT 0
) STRICT;
CREATE UNIQUE INDEX idx_LINKS_link ON LINKS(link);
