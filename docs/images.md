IMAGES AND COVERS

As of EbookMaker 0.9, image filesize and dimension limits are being set differently.

EbookMaker now considers three types of images it finds in html, and handles them differently from other images:

1. inline images
    `<img src="unicorn.png" alt="Image of a Unicorn" />`
2. linked images
    `<a href="bigunicorn.png" title="Expanded Image of a Unicorn" />Click for larger Unicorn</a>`
3. cover images
   These can come in 4 flavors (in priority order):
    1. coverpage relation
        `<link href="unicorn_image.jpg" rel="coverpage" />`  or 
    2. coverpage id
        `<img src="unicorn_image.jpg" id="coverpage" alt="front jacket" />`
    3. image with 'cover' in the url
        `<img src="unicorn_cover.jpg" alt="front jacket" />`
    4. image with 'title' in the url
        `<img src="unicorn_titlepage.jpg" alt="front jacket" />`

Ebookmaker doesn't like to have duplicate covers, so it takes the first cover of sufficient size (>200x200), creates a cover wrapper for it, and tries to remove duplicates.

Ebookmaker doesn't touch HTML or image files submitted to Project Gutenberg and displayed as HTML books. However, it transforms both HTML and image files for inclusion in EPUB and Kindle. Cover images displayed on Project Gutenberg are sized and processed by EbookMaker, and when no cover is present, an abstract cover is generated for the book.

For compatibility, Ebookmaker > 0.9 creates "wrapper" files for linked images. Submitters do not need to create wrapper files.

Images submitted for use in HTML should be sized and compressed so that load times are reasonably short and they look good on screens.

Ebookmaker 0.9 has relaxed some limits on image sizes used inside EPUB and Kindle, considering advances in device power and network speed. Before version 0.9, any image or cover larger than 128KB was compressed to  fit under 128KB. Similarly, images and covers wider than 800 px or taller than 1280 px were proportionately scaled down to fit. In version 0.9, the limits depend on the type of the image. 

- inline images are compressed if they are larger than 256KB and scaled if they are larger than 800x1280.
- linked images and cover images are compressed if they are larger than 1MB and scaled if they are larger than 5000x5000

Industry specifications for book cover images have changed in the last few years. Amazon now requires that commercial ebook covers have _minimum_ dimensions of "at least 1200 pixels in width or 1800 pixels in height." They're more relaxed for self-published covers; KDP suggests minimum dimensions of 625 x 1000 px and ideal dimensions of 1600 x 2560. New Project Gutenberg books should have covers of quality commensurate with industry practice.

Since cover images specified by the coverpage relation are not displayed in HTML, there is no need to limit their size (within reason!!!)

Suggested Guidelines for cover and image submissions to Project Gutenberg:

1. Submitted cover images should be at least 625 x 1000 px and ideally larger. The should be not exceed 1MB in size unless specified by a coverpage relation.

2. Submitted images should be less than 256KB for inline images and less than 1MB for linked images.




