from downward import portfolios

portfolio = [
    [1, ['--search', 'astar(blind())']],
    [2, ['--search', 'astar(lmcut())']],
]

def test_write_and_read(tmpdir):
    portfolio_file = tmpdir.join('test-pf.py')
    portfolio_file.write(portfolios.create_portfolio_script(portfolio, optimal=True))
    assert portfolios.import_portfolio(str(portfolio_file)) == portfolio

