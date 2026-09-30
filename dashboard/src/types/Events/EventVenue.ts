export interface EventVenue {
	name: string
	creation: string
	modified: string
	owner: string
	modified_by: string
	docstatus: 0 | 1 | 2
	parent?: string
	parentfield?: string
	parenttype?: string
	idx?: number
	/**	Venue Name : Data	*/
	venue_name: string
	/**	Address : Small Text	*/
	address: string
	/**	Type : Select	*/
	type?: "Embed Google Maps" | "Open Street Map"
	/**	Google Maps Embed Code : Code - Open a place on Google maps then click on share	*/
	google_maps_embed_code?: string
	/**	Longitude : Float	*/
	longitude?: number
	/**	Latitude : Float	*/
	latitude?: number
	/**	Location : Geolocation	*/
	location?: any
}
