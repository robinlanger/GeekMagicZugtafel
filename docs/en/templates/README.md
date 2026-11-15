# Template catalog

Ready-made pages for the display. Each one has its own page with an example picture, all options, setup steps and notes on privacy. Add a page to the `pages:` list in `config.yaml` and restart the server, see [Server configuration](../configuration.md).

## Time & weather

### clock

![Preview of the clock page](../../img/templates/clock.png)

A large clock with weekday and date, and the starting point for your own pages. [Details](clock.md)

### weather

![Preview of the weather page](../../img/templates/weather.png)

Current weather and the next four hours for one place, from the free Open-Meteo service. [Details](weather.md)

## Server & smart home

### kuma

![Preview of the kuma page](../../img/templates/kuma-down.png)

State of an Uptime Kuma status page: all green, or which services are down and since when. [Details](kuma.md)

## AI & development

### ai

![Preview of the ai page](../../img/templates/ai-claude.png)

How much of your AI plan you have used. Provider `claude`: the 5-hour and weekly limits of your Claude plan, sent by Claude Code's status line. [Details](ai.md)

## Transport

### bahn

![Preview of the bahn page](../../img/templates/bahn.png)

Live departures for a German station with delays, platform changes and cancellations. [Details](bahn.md)

## Your own pages

Pages are a folder with a small Python file and a Jinja template. [Writing pages](../writing-pages.md) walks you through it.
