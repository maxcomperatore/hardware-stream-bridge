# Third-Party Attributions

This project includes or uses the following third-party components, each governed by their respective licenses:

## Dinkie Icons

**Source:** [@iconify-json/dinkie-icons](https://www.npmjs.com/package/@iconify-json/dinkie-icons)  
**Version:** 1.2.0  
**License:** MIT  
**License Text:** https://github.com/iconify/icon-sets/blob/master/LICENSE

Dinkie Icons are a minimalist pixel-art icon set used throughout this project for UI components. Icons are fetched from the Iconify CDN and stored locally in `static/icons/dinkie/`.

### Usage

The following scripts handle Dinkie icon management:
- `scripts/download_dinkie_icons.py` - Fetches icons from Iconify CDN
- `scripts/fetch_one_dinkie.py` - Utility to fetch individual icons
- `scripts/migrate_dinkie_urls.py` - Migrates from CDN URLs to local paths

---

## License Compatibility

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0)**.

The MIT license used by Dinkie Icons is compatible with GPL-3.0. Under GPL-3.0 terms, all distributed code and assets must be made available under compatible terms.

---

For more information about licenses, see:
- [GPL-3.0 License](./LICENSE)
- [MIT License](https://opensource.org/licenses/MIT)
