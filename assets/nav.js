(function () {
  // 检测当前页面: 在 /pages/ 下还是根目录下
  var isPages = location.pathname.indexOf('/pages/') !== -1;
  var prefix = isPages ? '..' : '.';

  // 每个链接: [显示名, href(相对于当前页面), id]
  var links = [
    { label: '首页',       href: isPages ? '../index.html' : 'index.html',             id: 'home' },
    { label: 'GS145',      href: prefix + '/pages/gs145.html',                         id: 'gs145' },
    { label: 'QDII',       href: prefix + '/pages/qdii.html',                          id: 'qdii' },
    { label: 'Top100',     href: prefix + '/pages/top100.html',                        id: 'top100' },
    { label: 'ETF矩阵',    href: prefix + '/pages/etf_matrix.html',                    id: 'etf_matrix' },
    { label: '新高',       href: prefix + '/pages/new_high.html',                       id: 'new_high' },
    { label: '持仓',       href: prefix + '/pages/holding.html',                        id: 'holding' },
    { label: '量化',       href: prefix + '/pages/quant_strategy.html',               id: 'quant_strategy' },
    { label: '观点',       href: prefix + '/pages/wu2198.html',                       id: 'wu2198' },
    { label: '免责',       href: prefix + '/index.html#disclaimer',                     id: 'disclaimer' }
  ];

  // 判断当前哪个链接是 active
  var path = location.pathname.split('/').pop() || 'index.html';
  if (path === '') path = 'index.html';

  // 构建 nav-links HTML
  var navLinksHTML = '';
  for (var i = 0; i < links.length; i++) {
    var cls = (path === links[i].href.split('/').pop().split('#')[0] || '') ? ' class="active"' : '';
    navLinksHTML += '<a' + cls + ' href="' + links[i].href + '">' + links[i].label + '</a>';
  }

  // 构建完整 header
  var brandHref = isPages ? '../index.html' : 'index.html';
  var html =
    '<header class="site-header">' +
    '  <nav class="nav">' +
    '    <a class="brand" href="' + brandHref + '" aria-label="基金观察台首页">' +
    '      <span class="brand-mark">F</span>' +
    '      <span>基金观察台</span>' +
    '    </a>' +
    '    <div class="nav-links" aria-label="主要分类">' +
    navLinksHTML +
    '    </div>' +
    '  </nav>' +
    '</header>';

  // 插入到 body 最前面
  document.body.insertAdjacentHTML('afterbegin', html);
})();
