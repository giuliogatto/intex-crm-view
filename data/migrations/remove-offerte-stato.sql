-- Migration to drop the unused stato column from the offerte_testate table
ALTER TABLE offerte_testate DROP COLUMN IF EXISTS stato;
