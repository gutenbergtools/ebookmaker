isDebug = false;

/**	getPagedMinimumWidth(pageElement)
 * @param {*} pageElement - an HTML element
 * @returns {number} the minimum page width
 */
function getPageMinimumWidth(pageElement) {
	// Custom requested [injected script](https://github.com/gutenbergtools/ebookmaker/issues/289#issuecomment-3249911801)
	return Math.max(
		pageElement.scrollWidth,
		pageElement.offsetWidth,
		pageElement.clientWidth,
		// assuming that `document` refers to `page_element`; then this following code is assumed:
		pageElement.documentElement.scrollWidth,
		pageElement.documentElement.offsetWidth,
		pageElement.documentElement.clientWidth
	);
}

// Follows Documentation Example: https://pagedjs.org/en/documentation/10-handlers-hooks-and-custom-javascript/
class PG_PagedJS_Hook_Handler extends Paged.Handler {
	constructor(chunker, polisher, caller) {
		super(chunker, polisher, caller);
	}

	afterRendered(pages) {
		// console.log(`pagedjs_hooks.js::pagedjs::afterRendered()::total page count: ${pages.length}`);

		// if you want global minimum page width
		let minimumWidth = 0;
		pages.forEach((page) => {
			pageElement = page.element;

			minimumWidth = max(minimumWidth, getPageMinimumWidth(pageElement));

			if(isDebug) {
				console.log(`pagedjs_hooks.js::pagedjs::afterRendered()::current page minimum width: ${minimumWidth}`);
			}
		});

		/*
		// if you want to just sample a random/first page (assuming that there is at least one page)
		const random_page_number = Math.floor(Math.random() * pages.length);
		const sample_page = pages[random_page_number]; // replace `random_page_number` w/ `0` if only first page
		const minimum_width = get_page_minimum_width(sample_page);
		*/

		console.log(`pagedjs_hooks.js::pagedjs::afterRendered()::global page minimum width: ${minimumWidth}`);
	}
}

// Note: [var Paged = /*#__PURE__*/Object.freeze(...](https://unpkg.com/pagedjs@0.4.3/dist/paged.polyfill.js) reserves `Paged` as a global var
Paged.registerHandlers(PG_PagedJS_Hook_Handler);