name: bot
on:
  schedule:
    - cron: '3,33 * * * *'
  workflow_dispatch:
permissions:
  contents: write
concurrency:
  group: bot
  cancel-in-progress: false
jobs:
  run:
    runs-on: ubuntu-latest
    timeout-minutes: 29
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: |
          git config user.name bot
          git config user.email bot@users.noreply.github.com
          for i in 1 2 3 4 5 6; do
            python bot.py || true
            case $i in
              1|3|6)
                git add state.json
                git commit -m tick || true
                git pull --rebase -X theirs origin main || true
                git push || true
                ;;
            esac
            if [ $i -lt 6 ]; then sleep 280; fi
          done
