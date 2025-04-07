Changelog
==========

3.5.0 - January 8 2025
----------------------

- Added Python 3.13 support and removed Python 3.8 support
- Enhanced type hints throughout the codebase
- Replaced pkg_resources with importlib.metadata
- Fixed license name reference to correct METADATA issue
- Moved to Ruff for code formatting (replacing Black & isort)
- Documentation updates:
- Upgraded various dependencies:

3.4.1 - September 22, 2023
--------------------------

- Fix missing typing_extensions and mypy_extensions dependencies (#867) @ktbyers and @nemith

3.4.0 - October 31 2023
-----------------------

- Added plugins architecture image to plugins docs (#802) @dmulyalin
- Bump mistune from 0.8.4 to 2.0.3 (#813) @dependabot
- Fix wrongly return True when a comparison returns NotImplemented (#814) @ubaumann
- Bump nbconvert from 5.5.0 to 6.3.0 (#815) @dependabot
- Bump nbconvert from 6.3.0 to 6.5.1 (#817) @dependabot
- DockerFile Poetry Install Update (#820) @h4ndzdatm0ld
- Fix broken "Configuration" link (#828) @dgjustice
- Bump certifi from 2021.10.8 to 2022.12.7 (#831) @dependabot
- Bump jupyter-core from 4.9.2 to 4.11.2 (#832) @dependabot
- log number of hosts to run on correctly (#823) @txSangyj
- Upgrade poetry and readthedocs to use dependency groups (#835) @ktbyers
- Fix pylama breakage (pep8 reference no longer works) (#836) @ktbyers
- Bump requests from 2.28.2 to 2.31.0 (#844) @dependabot
- Bump cryptography from 39.0.1 to 41.0.3 (#853) @dependabot
- Make filter objects F, NOT_F, AND and OR comparable (#854) @ubaumann
- Update dependencies (#855) @ubaumann
- Update tasks.ipynb (#856) @lucasmarcel
- Bump version to 3.4.0 (#858) @ogenstad

3.3.0 - April 9, 2022
----------------------

- Create codeql-analysis.yml (#742) @dbarrosop
- fixed a typo (#767) @giorgiga
- Removing jinja2 leftover from configuration (#768) @ubaumann
- Deprecate py3.6 (#780) @ubaumann
- Bump paramiko from 2.9.2 to 2.10.1 (#792) @dependabot
- Bump notebook from 6.4.8 to 6.4.10 (#794) @dependabot
- bump version to 3.3.0 (#796) @dbarrosop

3.2.0 - November 16 2021
------------------------

- update gha snok/install-poetry (#736) @dbarrosop
- Update pygments because of vulnerabilities (#732) @ubaumann
- Replace pkg_resources with importlib (#731) @ubaumann
- Fix GitHub actions MacOS arch failure (#729) @ktbyers
- Minor doc error on NORNIR_RUNNER_OPTIONS environment variable (#725) @ktbyers
- Correct configuration order preference error (#728) @ktbyers
- Update task_results.ipynb (#715) @MajesticFalcon
- fixing domain name typo (#704) @marco-minervino
- update ruamel dependency (#694) @itdependsnetworks
- fixed stubs for mypy 0.900 (#696) @dbarrosop

3.1.1 - April 26 2021
---------------------

- address UTF-8 error on windows (#654) @dbarrosop
- remove state property from Nornir class (#669) @brandomando
- Evaluate a host's group outside groups evaluation (#677) @bytinbit
- Nornir Filtering Deep Dive How To (#674) @writememe

3.1.0 - February 27 2021
------------------------

- F filter now supports `any` for non-list values #608 @dbarrosop
- Corrected spelling in processors.ipynb (#635) @jmcguir
- phase out discourse in favour of discussions (#622) @dbarrosop
- Create py.typed (#636) @Kircheneer
- improvements to data resolution (#623) @dbarrosop
- added method to ParentsGroup to add a group easily (#624) @kpeterson-sf
- For the Result object doc string there is a typo in the host description. (#618) @LongBeachHXC
- fixed window build hangs if using cached dependencies (#614) @dbarrosop
- Severity_level was override when task is flag as failed (#612) @FloLaco
- fix "GitHub Actions: Deprecating set-env and add-path commands" (#613) @dbarrosop
- Fix InitNornir example in docs/configuration/index.rst (#598) @ubaumann
- Docs logging fix and Pin Poetry (#600) @ktbyers
- Fix nornir_nos filter in inventory tutorial (#596) @ubaumann
- Fix linking problems in tutorial Inventory.ipynb (#589) @kimdoanh89
- added information about plugins to the README (#587) @dbarrosop

3.0.0 - September 4 2020
------------------------

First nornir 3 release, see `upgrading notes <https://nornir.readthedocs.io/en/3.0.0/upgrading/2_to_3.html>`_ for details
