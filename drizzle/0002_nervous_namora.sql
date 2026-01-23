CREATE TABLE `alertSettings` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`projectId` int NOT NULL,
	`priceChangePercent` int,
	`scoreChangePoints` int,
	`enabled` int NOT NULL DEFAULT 1,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `alertSettings_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `comparisons` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`name` varchar(255) NOT NULL,
	`projectIds` text NOT NULL,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `comparisons_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `watchlist` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`projectId` int NOT NULL,
	`addedAt` timestamp NOT NULL DEFAULT (now()),
	`notes` text,
	`alertPrice` varchar(64),
	`alertScore` int,
	CONSTRAINT `watchlist_id` PRIMARY KEY(`id`)
);
