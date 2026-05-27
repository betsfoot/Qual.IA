-- ============================================================
--  Qual.IA — Setup Supabase (à coller dans SQL Editor)
--  Une seule fois, avant le premier déploiement.
-- ============================================================

-- Table des utilisateurs
CREATE TABLE IF NOT EXISTS users (
    username      TEXT PRIMARY KEY,
    nom           TEXT NOT NULL,
    role          TEXT NOT NULL,
    salt          TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Table des notifications workflow
CREATE TABLE IF NOT EXISTS notifications (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ref                  TEXT NOT NULL,
    categorie            TEXT NOT NULL,
    statut               TEXT NOT NULL,
    acteur               TEXT NOT NULL,
    date                 TIMESTAMPTZ NOT NULL,
    message              TEXT NOT NULL,
    roles_destinataires  JSONB NOT NULL DEFAULT '[]',
    lue_par              JSONB NOT NULL DEFAULT '[]'
);

-- Colonne email pour les notifications (ajout idempotent)
ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT DEFAULT '';

-- Désactiver RLS (accès serveur direct via clé API)
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
ALTER TABLE notifications DISABLE ROW LEVEL SECURITY;

-- Index pour accélérer les requêtes de notifications par date
CREATE INDEX IF NOT EXISTS idx_notifications_date ON notifications (date DESC);

-- Table des dossiers qualité (références + documents AMDEC/Gamme)
CREATE TABLE IF NOT EXISTS dossiers (
    categorie     TEXT NOT NULL,
    code          TEXT NOT NULL,
    metadata      JSONB NOT NULL DEFAULT '{}',
    data          JSONB NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (categorie, code)
);

ALTER TABLE dossiers DISABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_dossiers_categorie ON dossiers (categorie);
