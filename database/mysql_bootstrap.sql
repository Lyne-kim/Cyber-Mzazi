CREATE DATABASE IF NOT EXISTS cyber_mzazi
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'cyber_mzazi'@'%' IDENTIFIED BY 'change_this_password';

GRANT ALL PRIVILEGES ON cyber_mzazi.* TO 'cyber_mzazi'@'%';
FLUSH PRIVILEGES;
