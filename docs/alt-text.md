Ebookmaker encourages proper use of the alt attribute to make books with images more accessible to the reading disabled. Ebookmaker ensures that every `img` element has an `alt` attribute and issues warnings if the alt attribute is empty.

Often the `alt` attribute should be left empty:

1. when the image is purely decorative or used to help with the visual presentation of text. It would be disruptive to a person using text-to-speach or a braille reader to have the image described. In such a case, add a`role` attribute with value `presentation`: `<img src="image.png" alt="" role="presentation">` and the warning message will be suppressed.

2. when the image is well described by associated text. Often an image from a book will appear above a descriptive caption. For this reason, Ebookmaker will not emit a warning message if it appears inside a `<figure>` element containing a `<figcaption>`, or if the img has a `aria-labelledby` attribute: `<img src="image.png" alt="" aria-labelledby="some_id_in_file">` But when relying on a caption text, make sure it is describing what a sighted reader sees. Some captions comment on the image without describing it.


Accessibiity Tutorial:
https://www.w3.org/WAI/tutorials/images/

Using `aria-labelledby`:
https://www.w3.org/WAI/WCAG21/Techniques/aria/ARIA16

Other helpful guides:
https://publishers.asn.au/BooksWithoutBarriers
https://axesslab.com/alt-texts/
https://accessibility.huit.harvard.edu/describe-content-images